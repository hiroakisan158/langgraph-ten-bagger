from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage, get_buffer_string, filter_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command
import asyncio
from typing import Literal
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError
import time
import functools

# Load environment variables from .env file
load_dotenv()
from open_deep_research.configuration import (
    Configuration, 
)
from open_deep_research.state import (
    AgentState,
    AgentInputState,
    SupervisorState,
    ResearcherState,
    ResearchQuestion,
    ConductResearch,
    ResearchComplete,
    ResearcherOutputState
)
from open_deep_research.prompts_jp import (
    transform_messages_into_research_topic_prompt,
    stock_analysis_researcher_system_prompt,
    compress_research_system_prompt,
    compress_research_simple_human_message,
    stock_analysis_final_report_prompt,
    lead_researcher_prompt
)


    
from open_deep_research.utils import (
    get_today_str,
    is_token_limit_exceeded,
    get_model_token_limit,
    get_all_tools,
    openai_websearch_called,
    anthropic_websearch_called,
    remove_up_to_last_ai_message,
    get_api_key_for_model,
    get_notes_from_tool_calls,
    think_tool
)

# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

# Rate limiting aware retry decorator
def rate_limit_retry(func):
    @functools.wraps(func)
    @retry(
        stop=stop_after_attempt(5),  # リトライ回数を5回に増加
        wait=wait_exponential(multiplier=2, min=10, max=120),  # より長い待機時間
        retry=retry_if_exception_type((RateLimitError, Exception)),
        reraise=True
    )
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in [
                "rate_limit_exceeded", "rate limit", "too many requests", 
                "429", "quota exceeded", "tokens per min"
            ]):
                # レート制限の場合はより長く待機
                wait_time = 30 + (5 * getattr(wrapper, '_retry_count', 0))
                print(f"Rate limit detected, waiting {wait_time} seconds before retry: {e}")
                await asyncio.sleep(wait_time)
                wrapper._retry_count = getattr(wrapper, '_retry_count', 0) + 1
            raise
    return wrapper

@rate_limit_retry
async def write_research_brief(state: AgentState, config: RunnableConfig)-> Command[Literal["research_supervisor"]]:
    configurable = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    research_model = configurable_model.with_structured_output(ResearchQuestion).with_retry(stop_after_attempt=configurable.max_structured_output_retries).with_config(research_model_config)
    
    # プロンプトをフォーマット
    processed_prompt = transform_messages_into_research_topic_prompt.format(
        messages=get_buffer_string(state.get("messages", [])),
        date=get_today_str()
    )
    
    response = await research_model.ainvoke([HumanMessage(content=processed_prompt)])
    return Command(
        goto="research_supervisor", 
        update={
            "research_brief": response.research_brief,
            "supervisor_messages": {
                "type": "override",
                "value": [
                    SystemMessage(content=lead_researcher_prompt.format(
                        date=get_today_str(),
                        max_concurrent_research_units=configurable.max_concurrent_research_units
                    )),
                    HumanMessage(content=response.research_brief)
                ]
            }
        }
    )


@rate_limit_retry
async def supervisor(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor_tools"]]:
    configurable = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]
    research_model = configurable_model.bind_tools(lead_researcher_tools).with_retry(stop_after_attempt=configurable.max_structured_output_retries).with_config(research_model_config)
    supervisor_messages = state.get("supervisor_messages", [])
    response = await research_model.ainvoke(supervisor_messages)
    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1
        }
    )


async def supervisor_tools(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor", "__end__"]]:
    configurable = Configuration.from_runnable_config(config)
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]
    # Exit Criteria
    # 1. We have exceeded our max guardrail research iterations
    # 2. No tool calls were made by the supervisor
    # 3. The most recent message contains a ResearchComplete tool call and there is only one tool call in the message
    exceeded_allowed_iterations = research_iterations >= configurable.max_researcher_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete_tool_call = any(tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls)
    if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", "")
            }
        )
    # Otherwise, conduct research and gather results.
    try:
        # Handle all tool calls
        all_tool_calls = most_recent_message.tool_calls
        all_conduct_research_calls = [tool_call for tool_call in all_tool_calls if tool_call["name"] == "ConductResearch"]
        think_tool_calls = [tool_call for tool_call in all_tool_calls if tool_call["name"] == "think_tool"]
        
        conduct_research_calls = all_conduct_research_calls[:configurable.max_concurrent_research_units]
        overflow_conduct_research_calls = all_conduct_research_calls[configurable.max_concurrent_research_units:]
        
        # Handle ConductResearch calls
        coros = [
            researcher_subgraph.ainvoke({
                "researcher_messages": [
                    HumanMessage(content=tool_call["args"]["research_topic"])
                ],
                "research_topic": tool_call["args"]["research_topic"]
            }, config) 
            for tool_call in conduct_research_calls
        ]
        tool_results = await asyncio.gather(*coros)
        tool_messages = [ToolMessage(
                            content=observation.get("compressed_research", "Error synthesizing research report: Maximum retries exceeded"),
                            name=tool_call["name"],
                            tool_call_id=tool_call["id"]
                        ) for observation, tool_call in zip(tool_results, conduct_research_calls)]
        
        # Handle think_tool calls
        for think_call in think_tool_calls:
            reflection = think_call["args"].get("reflection", "No reflection provided")
            tool_messages.append(ToolMessage(
                content=f"Reflection recorded: {reflection}",
                name="think_tool",
                tool_call_id=think_call["id"]
            ))
        # Handle any tool calls made > max_concurrent_research_units
        for overflow_conduct_research_call in overflow_conduct_research_calls:
            tool_messages.append(ToolMessage(
                content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {configurable.max_concurrent_research_units} or fewer research units.",
                name="ConductResearch",
                tool_call_id=overflow_conduct_research_call["id"]
            ))
        raw_notes_concat = "\n".join(["\n".join(observation.get("raw_notes", [])) for observation in tool_results])
        return Command(
            goto="supervisor",
            update={
                "supervisor_messages": supervisor_messages + tool_messages,
                "raw_notes": [raw_notes_concat]
            }
        )
    except Exception as e:
        if is_token_limit_exceeded(e, configurable.research_model):
            print(f"Token limit exceeded while reflecting: {e}")
        else:
            print(f"Other error in reflection phase: {e}")
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", "")
            }
        )


supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_edge(START, "supervisor")
supervisor_subgraph = supervisor_builder.compile()


@rate_limit_retry
async def researcher(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher_tools"]]:
    '''
    This node is responsible for deciding which tools to call based on the research task and executing them by calling the researcher_tools node.
    '''
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])
    tools = await get_all_tools(config)
    if len(tools) == 0:
        raise ValueError("No tools found to conduct research: Please configure either your search API or add MCP tools to your configuration.")
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
        "tags": ["langsmith:nostream"]
    }
    # 株式分析特化のシステムプロンプトを使用
    researcher_system_prompt = stock_analysis_researcher_system_prompt.format(mcp_prompt=configurable.mcp_prompt or "", date=get_today_str())
    # Bind ALL tools to the model so LLM can see them
    research_model = configurable_model.bind_tools(tools).with_retry(stop_after_attempt=configurable.max_structured_output_retries).with_config(research_model_config)
    # LLM decides which tools to call based on the research task
    response = await research_model.ainvoke([SystemMessage(content=researcher_system_prompt)] + researcher_messages)
    return Command(
        goto="researcher_tools",
        update={
            "researcher_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
        }
    )


@rate_limit_retry
async def execute_tool_safely(tool, args, config):
    try:
        return await tool.ainvoke(args, config)
    except Exception as e:
        return f"Error executing tool: {str(e)}"


async def researcher_tools(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher", "compress_research"]]:
    '''
    This node is responsible for executing the tool calls that the LLM decided to make.
    '''
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1]
    # Early Exit Criteria: No tool calls (or native web search calls)were made by the researcher
    if not most_recent_message.tool_calls and not (openai_websearch_called(most_recent_message) or anthropic_websearch_called(most_recent_message)):
        return Command(
            goto="compress_research",
        )
    # Otherwise, execute tools and gather results.
    tools = await get_all_tools(config)
    tools_by_name = {tool.name if hasattr(tool, "name") else tool.get("name", "web_search"):tool for tool in tools}
    # Get the tool calls that the LLM decided to make
    tool_calls = most_recent_message.tool_calls
    coros = [execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config) for tool_call in tool_calls]
    #  Run the selected tools in parallel
    observations = await asyncio.gather(*coros)
    tool_outputs = [ToolMessage(
                        content=observation,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    ) for observation, tool_call in zip(observations, tool_calls)]
    
    # Late Exit Criteria: We have exceeded our max guardrail tool call iterations or the most recent message contains a ResearchComplete tool call
    # These are late exit criteria because we need to add ToolMessages
    if state.get("tool_call_iterations", 0) >= configurable.max_react_tool_calls or any(tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls):
        return Command(
            goto="compress_research",
            update={
                "researcher_messages": tool_outputs,
            }
        )
    return Command(
        goto="researcher",
        update={
            "researcher_messages": tool_outputs,
        }
    )


@rate_limit_retry
async def compress_research(state: ResearcherState, config: RunnableConfig):
    configurable = Configuration.from_runnable_config(config)
    synthesis_attempts = 0
    synthesizer_model = configurable_model.with_config({
        "model": configurable.compression_model,
        "max_tokens": configurable.compression_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.compression_model, config),
        "tags": ["langsmith:nostream"]
    })
    researcher_messages = state.get("researcher_messages", [])
    # Update the system prompt to now focus on compression rather than research.
    researcher_messages.append(HumanMessage(content=compress_research_simple_human_message))
    while synthesis_attempts < 3:
        try:
            response = await synthesizer_model.ainvoke([SystemMessage(content=compress_research_system_prompt.format(date=get_today_str()))] + researcher_messages)
            return {
                "compressed_research": str(response.content),
                "raw_notes": ["\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])]
            }
        except Exception as e:
            synthesis_attempts += 1
            if is_token_limit_exceeded(e, configurable.research_model):
                researcher_messages = remove_up_to_last_ai_message(researcher_messages)
                print(f"Token limit exceeded while synthesizing: {e}. Pruning the messages to try again.")
                continue         
            print(f"Error synthesizing research report: {e}")
    return {
        "compressed_research": "Error synthesizing research report: Maximum retries exceeded",
        "raw_notes": ["\n".join([str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])])]
    }


researcher_builder = StateGraph(ResearcherState, output=ResearcherOutputState, config_schema=Configuration)
researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)
researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("compress_research", END)
researcher_subgraph = researcher_builder.compile()


@rate_limit_retry
async def final_report_generation(state: AgentState, config: RunnableConfig):
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []},}
    configurable = Configuration.from_runnable_config(config)
    writer_model_config = {
        "model": configurable.final_report_model,
        "max_tokens": configurable.final_report_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.research_model, config),
    }
    
    findings = "\n".join(notes)
    max_retries = 3
    current_retry = 0
    while current_retry <= max_retries:
        # 株式分析特化の最終レポート生成プロンプトを使用
        final_report_prompt = stock_analysis_final_report_prompt.format(
            compressed_research=findings,
            research_brief=state.get("research_brief", ""),
            messages=get_buffer_string(state.get("messages", [])),
            date=get_today_str()
        )
        try:
            final_report = await configurable_model.with_config(writer_model_config).ainvoke([HumanMessage(content=final_report_prompt)])
            return {
                "final_report": final_report.content, 
                "messages": [final_report],
                **cleared_state
            }
        except Exception as e:
            if is_token_limit_exceeded(e, configurable.final_report_model):
                if current_retry == 0:
                    model_token_limit = get_model_token_limit(configurable.final_report_model)
                    if not model_token_limit:
                        return {
                            "final_report": f"Error generating final report: Token limit exceeded, however, we could not determine the model's maximum context length. Please update the model map in deep_researcher/utils.py with this information. {e}",
                            **cleared_state
                        }
                    findings_token_limit = model_token_limit * 4
                else:
                    findings_token_limit = int(findings_token_limit * 0.9)
                print("Reducing the chars to", findings_token_limit)
                findings = findings[:findings_token_limit]
                current_retry += 1
            else:
                # If not a token limit exceeded error, then we just throw an error.
                return {
                    "final_report": f"Error generating final report: {e}",
                    **cleared_state
                }
    return {
        "final_report": "Error generating final report: Maximum retries exceeded",
        "messages": [final_report],
        **cleared_state
    }

deep_researcher_builder = StateGraph(AgentState, input=AgentInputState, config_schema=Configuration)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)
deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)
deep_researcher_builder.add_node("final_report_generation", final_report_generation)
deep_researcher_builder.add_edge(START, "write_research_brief")
deep_researcher_builder.add_edge("research_supervisor", "final_report_generation")
deep_researcher_builder.add_edge("final_report_generation", END)

deep_researcher = deep_researcher_builder.compile()
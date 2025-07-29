import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
from azure.data.tables import TableServiceClient
import uuid
import datetime
import asyncio
from langgraph.checkpoint.memory import MemorySaver
from open_deep_research.deep_researcher import deep_researcher_builder
from logger_config import configure_logging

load_dotenv()

# Set up logging
logger = configure_logging()

# Azure environments
# CONNECTION_STRING = os.getenv("CONNECTION_STRING")

############################################
# Deep Research Configuration
############################################
def get_deep_research_config():
    """Get Deep Research configuration from environment variables or defaults"""
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "max_structured_output_retries": 3,
            "allow_clarification": True,
            "max_concurrent_research_units": 5,
            "search_api": "tavily",
            "max_researcher_iterations": 3,
            "max_react_tool_calls": 5,
            "summarization_model": "openai:gpt-4.1-nano",
            "summarization_model_max_tokens": 8192,
            "research_model": "openai:gpt-4.1",
            "research_model_max_tokens": 10000,
            "compression_model": "openai:gpt-4.1-mini",
            "compression_model_max_tokens": 8192,
            "final_report_model": "openai:gpt-4.1",
            "final_report_model_max_tokens": 10000,
        }
    }

async def run_deep_research(user_input: str):
    """Run Deep Research with user input"""
    try:
        # Compile the graph
        graph = deep_researcher_builder.compile(checkpointer=MemorySaver())
        
        # Get configuration
        config = get_deep_research_config()
        
        # Run the research
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config
        )
        
        return result
    except Exception as e:
        logger.error(f"Deep Research error: {e}")
        return {"error": str(e)}

############################################
# Show title
############################################
st.title("Deep Research Assistant")
st.markdown("Ask me anything and I'll conduct comprehensive research for you!")

############################################
# Sidebar for configuration
############################################
with st.sidebar:
    st.header("Configuration")
    
    # Research settings
    st.subheader("Research Settings")
    max_concurrent = st.slider("Max Concurrent Research Units", 1, 10, 5)
    max_iterations = st.slider("Max Research Iterations", 1, 10, 3)
    allow_clarification = st.checkbox("Allow Clarification Questions", value=True)
    
    # Model settings
    st.subheader("Model Settings")
    research_model = st.selectbox(
        "Research Model",
        ["openai:gpt-4.1", "openai:gpt-4", "anthropic:claude-3-5-sonnet-20241022"],
        index=0
    )
    
    # Search settings
    st.subheader("Search Settings")
    search_api = st.selectbox(
        "Search API",
        ["tavily", "openai", "anthropic", "none"],
        index=0
    )

############################################
# Show chat history
############################################
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

############################################
# React to user input
############################################

if prompt := st.chat_input("What would you like me to research?"):
    # Show user message first
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Show assistant message placeholder
    with st.chat_message("assistant"):
        with st.spinner("Conducting research..."):
            # Update configuration based on sidebar settings
            config = get_deep_research_config()
            config["configurable"]["max_concurrent_research_units"] = max_concurrent
            config["configurable"]["max_researcher_iterations"] = max_iterations
            config["configurable"]["allow_clarification"] = allow_clarification
            config["configurable"]["research_model"] = research_model
            config["configurable"]["search_api"] = search_api
            
            # Run Deep Research
            result = asyncio.run(run_deep_research(prompt))
            
            if "error" in result:
                st.error(f"Research failed: {result['error']}")
                response_content = f"Sorry, I encountered an error during research: {result['error']}"
            else:
                # Extract the final report from the result
                final_report = result.get("final_report", "No report generated")
                
                # Display the research results
                st.markdown("## Research Results")
                st.markdown(final_report)
                
                # Add expandable sections for more details
                with st.expander("Research Process Details"):
                    if "notes" in result:
                        st.markdown("### Research Notes")
                        for note in result["notes"]:
                            st.markdown(f"- {note}")
                    
                    if "research_brief" in result:
                        st.markdown("### Research Brief")
                        st.markdown(result["research_brief"])
                
                response_content = final_report

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_content})


import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
from azure.data.tables import TableServiceClient
import uuid
import datetime
import asyncio
import json
import pathlib
from langgraph.checkpoint.memory import MemorySaver
from open_deep_research.deep_researcher import deep_researcher_builder
from open_deep_research.prompts_jp import (
    lead_researcher_prompt,
    transform_messages_into_research_topic_prompt,
    stock_analysis_researcher_system_prompt,
    compress_research_system_prompt,
    compress_research_simple_human_message,
    summarize_webpage_prompt,
    stock_analysis_final_report_prompt
)
from logger_config import configure_logging
from langfuse.langchain import CallbackHandler

load_dotenv()

# Set up logging
logger = configure_logging()

# Azure environments
# CONNECTION_STRING = os.getenv("CONNECTION_STRING")

# History file path
HISTORY_FILE = os.getenv("RESEARCH_HISTORY_FILE", "research_history.json")

############################################
# History Management Functions
############################################
def load_research_history_from_file():
    """Load research history from JSON file"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                
                # Validate each entry and filter out invalid ones
                valid_entries = []
                for entry in history_data:
                    if validate_history_entry(entry):
                        valid_entries.append(entry)
                    else:
                        logger.warning(f"Invalid history entry found and skipped: {entry.get('id', 'unknown')}")
                
                return valid_entries
    except Exception as e:
        logger.error(f"Error loading history file: {e}")
    return []

def save_research_history_to_file(history):
    """Save research history to JSON file"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving history file: {e}")

def save_research_history(query: str, result: dict, timestamp: str):
    """Save research history to session state and file"""
    if "research_history" not in st.session_state:
        st.session_state.research_history = load_research_history_from_file()
    
    # Serialize the result to make it JSON compatible
    serialized_result = serialize_result_for_json(result)
    
    history_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "query": query,
        "result": serialized_result
    }
    
    # Validate the entry before saving
    if not validate_history_entry(history_entry):
        logger.error("Invalid history entry structure, skipping save")
        return
    
    st.session_state.research_history.append(history_entry)
    
    # Keep only the last 50 entries to prevent memory issues
    if len(st.session_state.research_history) > 50:
        st.session_state.research_history = st.session_state.research_history[-50:]
    
    # Save to file
    save_research_history_to_file(st.session_state.research_history)

def get_research_history():
    """Get research history from session state or file"""
    if "research_history" not in st.session_state:
        st.session_state.research_history = load_research_history_from_file()
    return st.session_state.get("research_history", [])

def delete_research_history(history_id: str):
    """Delete a specific research history entry"""
    if "research_history" in st.session_state:
        st.session_state.research_history = [
            entry for entry in st.session_state.research_history 
            if entry['id'] != history_id
        ]
        # Save updated history to file
        save_research_history_to_file(st.session_state.research_history)

def clear_all_history():
    """Clear all research history"""
    if "research_history" in st.session_state:
        st.session_state.research_history = []
        # Remove history file
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)

def validate_history_entry(entry):
    """Validate that a history entry has all required keys"""
    required_keys = ['id', 'timestamp', 'query', 'result']
    return all(key in entry for key in required_keys)

def serialize_result_for_json(result, visited=None):
    """Convert result to JSON serializable format with circular reference protection"""
    if visited is None:
        visited = set()
    
    # Check for circular reference
    result_id = id(result)
    if result_id in visited:
        return "[Circular Reference]"
    
    visited.add(result_id)
    
    try:
        if isinstance(result, dict):
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    serializable_result[key] = value
                elif isinstance(value, list):
                    serializable_result[key] = [
                        serialize_result_for_json(item, visited) if not isinstance(item, (str, int, float, bool, type(None))) else item
                        for item in value
                    ]
                elif isinstance(value, dict):
                    serializable_result[key] = serialize_result_for_json(value, visited)
                else:
                    # Convert any other objects to string
                    serializable_result[key] = str(value)
            return serializable_result
        elif isinstance(result, list):
            return [
                serialize_result_for_json(item, visited) if not isinstance(item, (str, int, float, bool, type(None))) else item
                for item in result
            ]
        elif isinstance(result, (str, int, float, bool, type(None))):
            return result
        else:
            return str(result)
    finally:
        # Remove from visited set to allow reuse in different contexts
        visited.discard(result_id)

def display_history_entry(entry: dict):
    """Display a single history entry"""
    st.markdown(f"**Query:** {entry['query']}")
    st.markdown(f"**Timestamp:** {entry['timestamp']}")
    
    if "error" in entry["result"]:
        st.error(f"Research failed: {entry['result']['error']}")
    else:
        final_report = entry["result"].get("final_report", "No report generated")
        st.markdown("### Research Results")
        st.markdown(final_report)
        
        # Add expandable sections for more details
        with st.expander("Research Process Details"):
            if "notes" in entry["result"]:
                st.markdown("### Research Notes")
                for note in entry["result"]["notes"]:
                    st.markdown(f"- {note}")
            
            if "research_brief" in entry["result"]:
                st.markdown("### Research Brief")
                st.markdown(entry["result"]["research_brief"])

############################################
# Deep Research Configuration
############################################
def get_deep_research_config():
    """Get Deep Research configuration from environment variables or defaults"""

    langfuse_handler = CallbackHandler()

    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "max_structured_output_retries": int(os.getenv("MAX_STRUCTURED_OUTPUT_RETRIES", "2")),  # 減らす
            "max_concurrent_research_units": int(os.getenv("MAX_CONCURRENT_RESEARCH_UNITS", "2")),  # 大幅に減らす
            "search_api": os.getenv("SEARCH_API", "tavily"),
            "max_researcher_iterations": int(os.getenv("MAX_RESEARCHER_ITERATIONS", "2")),  # 減らす
            "max_react_tool_calls": int(os.getenv("MAX_REACT_TOOL_CALLS", "3")),  # 減らす
            "summarization_model": os.getenv("SUMMARIZATION_MODEL", "openai:gpt-4o-mini"),
            "summarization_model_max_tokens": int(os.getenv("SUMMARIZATION_MODEL_MAX_TOKENS", "4096")),  # 減らす
            "research_model": os.getenv("RESEARCH_MODEL", "openai:gpt-4o-mini"),
            "research_model_max_tokens": int(os.getenv("RESEARCH_MODEL_MAX_TOKENS", "4096")),  # 減らす
            "compression_model": os.getenv("COMPRESSION_MODEL", "openai:gpt-4o-mini"),
            "compression_model_max_tokens": int(os.getenv("COMPRESSION_MODEL_MAX_TOKENS", "4096")),  # 減らす
            "final_report_model": os.getenv("FINAL_REPORT_MODEL", "openai:gpt-4o-mini"),
            "final_report_model_max_tokens": int(os.getenv("FINAL_REPORT_MODEL_MAX_TOKENS", "4096")),  # 減らす
        },
        "callbacks": [langfuse_handler]
    }
    
    return config

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
# Initialize session state
############################################
# Initialize chat history early
if "messages" not in st.session_state:
    st.session_state.messages = []

############################################
# Show title
############################################
st.title("Deep Research Assistant")
st.markdown("Ask me anything and I'll conduct comprehensive research for you!")

############################################
# Sidebar for configuration and history
############################################
with st.sidebar:
    # Add New Chat button
    if st.button("New Chat", type="primary"):
        # Clear chat messages
        if "messages" in st.session_state:
            st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # Prompt display section
    st.markdown("### 📋 Available Prompts")
    
    # Define available prompts with descriptions
    available_prompts = {
        "Lead Researcher Prompt": {
            "content": lead_researcher_prompt,
            "description": "🔍 リードリサーチャーのシステムプロンプト（調査全体の指揮・統制）"
        },
        "Transform Messages into Research Topic": {
            "content": transform_messages_into_research_topic_prompt,
            "description": "📝 メッセージを調査トピックに変換するプロンプト"
        },
        "Stock Analysis Researcher": {
            "content": stock_analysis_researcher_system_prompt,
            "description": "📊 株式分析リサーチャーのシステムプロンプト（銘柄分析の専門調査）"
        },
        "Compress Research System": {
            "content": compress_research_system_prompt,
            "description": "📝 調査結果圧縮のシステムプロンプト（情報整理・統合）"
        },
        "Compress Research Simple": {
            "content": compress_research_simple_human_message,
            "description": "📋 調査結果圧縮のシンプルメッセージ（簡易版）"
        },
        "Summarize Webpage": {
            "content": summarize_webpage_prompt,
            "description": "🌐 ウェブページ要約のプロンプト（情報抽出・要約）"
        },
        "Stock Analysis Final Report": {
            "content": stock_analysis_final_report_prompt,
            "description": "📈 株式分析最終レポートのプロンプト（投資判断レポート作成）"
        }
    }
    
    # Display all prompts in expandable sections
    for prompt_name, prompt_info in available_prompts.items():
        with st.expander(f"📝 {prompt_name}", expanded=False):
            st.caption(f"💡 {prompt_info['description']}")
            st.text_area(
                f"Content:",
                value=prompt_info['content'],
                height=200,
                disabled=True,
                help="このプロンプトは現在の調査で使用されています"
            )
    
    st.markdown("---")
    
    history = get_research_history()
    
    if history:        
        # Display history as a list with timestamps
        st.markdown("### 🔍 Recent Research")
        
        # Reverse to show newest first
        for i, entry in enumerate(reversed(history)):
            # Create a compact display for each history item
            timestamp = entry['timestamp']
            query = entry['query'][:20] + "..." if len(entry['query']) > 20 else entry['query']
            
            # Create a unique key for each history item
            history_key = f"history_{entry['id']}"
            
            # Create columns for button and delete button
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Display as a clickable button-like element that loads directly into chat
                if st.button(f"{query}", key=f"btn_{history_key}", help="Click to load into chat"):
                    # Ensure messages is initialized
                    if "messages" not in st.session_state:
                        st.session_state.messages = []
                    else:
                        st.session_state.messages = []
                    
                    # Add the research to chat history
                    st.session_state.messages.append({"role": "user", "content": entry['query']})
                    st.session_state.messages.append({"role": "assistant", "content": entry['result'].get("final_report", "No report generated")})
                    st.rerun()
            
            with col2:
                # Add delete button for each history item
                if st.button("🗑️", key=f"delete_{entry['id']}", help="Delete this research"):
                    delete_research_history(entry['id'])
                    st.rerun()
    else:
        st.info("No research history yet. Start by asking a question!")

############################################
# Show chat history
############################################
# Display chat messages (initialization is done earlier)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

############################################
# React to user input
############################################

if prompt := st.chat_input("What would you like me to research?"):
    # Ensure messages is initialized
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Show user message first
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Show assistant message placeholder
    with st.chat_message("assistant"):
        with st.spinner("Conducting research..."):
            # Run Deep Research
            result = asyncio.run(run_deep_research(prompt))
            
            # Save to history
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_research_history(prompt, result, timestamp)
            
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
    # Ensure messages is initialized
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": response_content})
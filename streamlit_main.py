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
from logger_config import configure_logging

load_dotenv()

# Set up logging
logger = configure_logging()

# Azure environments
# CONNECTION_STRING = os.getenv("CONNECTION_STRING")

# History file path
HISTORY_FILE = "research_history.json"

############################################
# History Management Functions
############################################
def load_research_history_from_file():
    """Load research history from JSON file"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
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

def serialize_result_for_json(result):
    """Convert result to JSON serializable format"""
    if isinstance(result, dict):
        serializable_result = {}
        for key, value in result.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                serializable_result[key] = value
            elif isinstance(value, list):
                serializable_result[key] = [
                    str(item) if not isinstance(item, (str, int, float, bool, type(None))) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                serializable_result[key] = serialize_result_for_json(value)
            else:
                # Convert any other objects to string
                serializable_result[key] = str(value)
        return serializable_result
    elif isinstance(result, (str, int, float, bool, type(None))):
        return result
    else:
        return str(result)

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
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "max_structured_output_retries": int(os.getenv("MAX_STRUCTURED_OUTPUT_RETRIES", "3")),
            "allow_clarification": os.getenv("ALLOW_CLARIFICATION", "true").lower() == "true",
            "max_concurrent_research_units": int(os.getenv("MAX_CONCURRENT_RESEARCH_UNITS", "5")),
            "search_api": os.getenv("SEARCH_API", "tavily"),
            "max_researcher_iterations": int(os.getenv("MAX_RESEARCHER_ITERATIONS", "3")),
            "max_react_tool_calls": int(os.getenv("MAX_REACT_TOOL_CALLS", "5")),
            "summarization_model": os.getenv("SUMMARIZATION_MODEL", "openai:gpt-4.1-nano"),
            "summarization_model_max_tokens": int(os.getenv("SUMMARIZATION_MODEL_MAX_TOKENS", "8192")),
            "research_model": os.getenv("RESEARCH_MODEL", "openai:gpt-4.1"),
            "research_model_max_tokens": int(os.getenv("RESEARCH_MODEL_MAX_TOKENS", "10000")),
            "compression_model": os.getenv("COMPRESSION_MODEL", "openai:gpt-4.1-mini"),
            "compression_model_max_tokens": int(os.getenv("COMPRESSION_MODEL_MAX_TOKENS", "8192")),
            "final_report_model": os.getenv("FINAL_REPORT_MODEL", "openai:gpt-4.1"),
            "final_report_model_max_tokens": int(os.getenv("FINAL_REPORT_MODEL_MAX_TOKENS", "10000")),
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
# Sidebar for configuration and history
############################################
with st.sidebar:
    history = get_research_history()
    
    if history:
        # Add New Chat button
        if st.button("New Chat", type="primary"):
            # Clear chat messages
            if "messages" in st.session_state:
                st.session_state.messages = []
            st.rerun()
        
        # Display history as a list with timestamps
        st.markdown("**Recent Research:**")
        
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
                if st.button(f"🔍 {query}", key=f"btn_{history_key}", help="Click to load into chat"):
                    if "messages" not in st.session_state:
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
    st.session_state.messages.append({"role": "assistant", "content": response_content})


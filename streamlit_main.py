import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
from azure.data.tables import TableServiceClient
import uuid
import datetime
# from table.chat_diary_table import ChatDiaryTable
# from category_map_renderer.chat_category_map_render import print_category_map
# from langgraph_categorizer.chat_categorizer import ChatCategorizer
from logger_config import configure_logging

load_dotenv()

# Set up logging
logger = configure_logging()

# Azure environments
# CONNECTION_STRING = os.getenv("CONNECTION_STRING")

############################################
# Show title
############################################
st.title("Let's find ten-baggers together!")

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

if prompt := st.chat_input("What is up?"):
    # Show user message first
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # # Get response from Langgraph
    # chat_categorizer = ChatCategorizer()
    # response = chat_categorizer.categorize_one_entity_and_save(prompt)

    # if "saved" in response:
    #     logger.info(response)
    #     st.success(response)
    # else:
    #     logger.error(response)
    #     st.error(response)

    # Simulate a response for demonstration purposes
    response = f"Echo: {prompt}"
    with st.chat_message("assistant"):
        st.markdown(response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})


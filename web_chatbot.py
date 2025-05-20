#!/usr/bin/env python3
"""
Web interface for the Gemini AI Chatbot.
This script provides a Streamlit-based web interface for interacting with Google's Gemini AI model.
"""

import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Gemini AI Chatbot",
    page_icon="🤖",
    layout="centered"
)

# Apply custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTextInput>div>div>input {
        border-radius: 20px;
    }
    .stChatMessage {
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Configure API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key or api_key == "your_api_key_here":
    st.error("No valid API key found. Please add your GOOGLE_API_KEY to the .env file.")
    st.info("You can get an API key from [Google AI Studio](https://makersuite.google.com/)")
    st.stop()

genai.configure(api_key=api_key)

# Set up the model
@st.cache_resource
def get_model():
    return genai.GenerativeModel('gemini-pro')

model = get_model()

# Initialize chat in session state
if "chat" not in st.session_state:
    # Set up system prompt to define personality
    system_prompt = """You are a helpful AI assistant with a friendly, casual tone.
    You excel at explaining technical concepts in simple terms."""
    
    # Initialize conversation with personality
    st.session_state.chat = model.start_chat(history=[
        {'role': 'user', 'parts': [system_prompt]},
        {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
    ])

# Initialize messages in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the chat title
st.title("🤖 Gemini AI Chatbot")
st.caption("A chatbot powered by Google's Gemini Pro model")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
prompt = st.chat_input("Ask something...")

# Process the prompt
if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            response = st.session_state.chat.send_message(prompt)
            message_placeholder.markdown(response.text)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            error_message = f"Error: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Sidebar with options
with st.sidebar:
    st.title("Options")
    
    # Clear chat button
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        # Reinitialize chat with personality
        system_prompt = """You are a helpful AI assistant with a friendly, casual tone.
        You excel at explaining technical concepts in simple terms."""
        
        st.session_state.chat = model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ['I understand! I\'ll be a friendly, helpful assistant who explains technical concepts simply.']}
        ])
        st.experimental_rerun()
    
    # About section
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This chatbot is powered by Google's Gemini Pro model.
    
    It can help you with:
    - Answering questions
    - Explaining concepts
    - Creative writing
    - Problem solving
    - And much more!
    """)

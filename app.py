import streamlit as st
import uuid
import json
import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Configure API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Set up logging directory
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "interactions.jsonl")

def get_llm_response(prompt, model="gpt-4"):
    """
    Get response from OpenAI API
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling LLM API: {str(e)}")
        return f"Error: {str(e)}"

def log_interaction(user_id, prompt, response):
    """
    Log user interaction to JSONL file
    """
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "anonymized_user_id": user_id,
        "prompt": prompt,
        "response": response
    }
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        st.error(f"Error logging interaction: {str(e)}")

# Initialize anonymized user ID in session state if not present
if 'anonymized_user_id' not in st.session_state:
    st.session_state.anonymized_user_id = str(uuid.uuid4())
    st.session_state.chat_history = []

# App title and description
st.title("LLM Interaction Study")
st.markdown("""
This application is part of a research study investigating interactions with Large Language Models.
Your interactions will be logged with an anonymous identifier.
""")

# Display the anonymized user ID (for reference purposes)
st.info(f"Your anonymous participant ID: **{st.session_state.anonymized_user_id}**")
st.markdown("**Please write down this ID** - you'll need to enter it in the survey later to link your interactions to your responses.")

# Chat interface
st.subheader("Chat with the AI")

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])

# User input
prompt = st.chat_input("Type your message here...")
if prompt:
    # Display user message
    st.chat_message("user").write(prompt)
    
    # Add to chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # Get LLM response
    with st.spinner("Thinking..."):
        response = get_llm_response(prompt)
    
    # Display assistant response
    st.chat_message("assistant").write(response)
    
    # Add to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Log the interaction
    log_interaction(st.session_state.anonymized_user_id, prompt, response)

# Additional information
st.sidebar.header("About this Study")
st.sidebar.markdown("""
### Instructions
1. Interact with the AI assistant using the chat interface
2. Complete all required interactions
3. Remember your anonymous ID
4. Complete the survey afterwards

### Survey Link
[Click here to access the survey](https://your-survey-link-here.com)

### Contact
For questions or concerns, please contact: researcher@example.com
""")
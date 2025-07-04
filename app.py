import streamlit as st
import uuid
import json
import datetime
import os
from openai import OpenAI

# --- Page Configuration ---
# Set the title and layout for the browser tab. This should be the first Streamlit command.
st.set_page_config(
    page_title="Neuroeconomics Learning Study",
    layout="wide"
)

# --- Fictional API Key Loading ---
# In a real app deployed on Streamlit Cloud, the key would be in st.secrets
# For local development, you might use a .env file.
# This code assumes the key is correctly set in your deployment environment (e.g., Streamlit Secrets).
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    # This is a fallback for local testing if you don't have st.secrets set up
    # It assumes you have a .env file.
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        st.error("OpenAI API key is not set. Please set it in your environment or Streamlit Secrets.")
        st.stop()
    client = OpenAI(api_key=OPENAI_API_KEY)


# --- Logging Setup ---
# This part remains the same for data collection.
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


# --- Core Functions ---
def get_llm_response(chat_history, model="gpt-4"):
    """
    Get response from OpenAI API based on the entire conversation history.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=chat_history, # Pass the whole history
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling LLM API: {str(e)}")
        return f"Error: {str(e)}"

def log_interaction(user_id, prompt, response):
    """
    Log user interaction to a user-specific JSONL file.
    """
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "anonymized_user_id": user_id,
        "prompt": prompt,
        "response": response
    }
    log_file = os.path.join(LOG_DIR, f"log_{user_id}.jsonl")
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        st.error(f"Error logging interaction: {str(e)}")

# --- Session State Initialization ---
# Ensures that each user gets a unique ID and their own chat history.
if 'anonymized_user_id' not in st.session_state:
    st.session_state.anonymized_user_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.page = "Landing" # Start on the landing page

# --- UI Layout (Using Pages) ---

def show_landing_page():
    """
    Displays the initial information page for the study.
    """
    st.title("Welcome to the Neuroeconomics Learning Study")
    st.header("About This Research Project")
    
    st.markdown(
        """
        You have been invited to participate in a research project that explores how using a Large Language Model (LLM) 
        [cite_start]during a learning task affects the ability to recall knowledge 48 hours later[cite: 146]. The findings will help 
        [cite_start]design evidence-based guidance for the effective use of AI tools in education[cite: 148].
        """
    )

    st.subheader("What Will You Be Doing?")
    st.markdown(
        """
        [cite_start]This study is a controlled experiment where you will first engage in independent study of provided materials on the topic of **Neuroeconomics**[cite: 151]. 
        [cite_start]Neuroeconomics is an interdisciplinary field that combines neuroscience, economics, and psychology to understand human decision-making[cite: 136].
        
        After the study period, you will complete a series of analytical tasks, including:
        * [cite_start]Analyzing business case studies where decision biases may have been involved[cite: 140].
        * [cite_start]Designing a simple experiment to test a neuroeconomic principle[cite: 141].
        * [cite_start]Developing strategic recommendations based on what you have learned[cite: 142].

        [cite_start]Your group has been assigned to use this chat interface to assist you during the application tasks[cite: 3]. Every interaction (your prompts and the AI's responses) 
        [cite_start]will be logged for later analysis to see which patterns of use predict better recall[cite: 147].
        """
    )

    st.info(f"Your anonymous participant ID is: **{st.session_state.anonymized_user_id}**\n\nPlease write this ID down. You will need it for the paper-based recall test later.")

    if st.button("Proceed to Chat Interface"):
        st.session_state.page = "Chat"
        st.experimental_rerun()


def show_chat_interface():
    """
    Displays the main chat interface for interacting with the LLM.
    """
    st.title("Neuroeconomics Learning Assistant")
    st.markdown(
        """
        Use this interface to ask questions and get help with the application tasks. This assistant is powered by **OpenAI's GPT-4 model** (ChatGPT). 
        [cite_start]Remember, all of your on-screen activity (prompts, timestamps, and model replies) is being recorded automatically[cite: 152].
        """
    )
    
    st.warning(f"Your Anonymous Participant ID: **{st.session_state.anonymized_user_id}**")
    
    st.subheader("Chat with the AI")

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # User input
    if prompt := st.chat_input("Ask a question about neuroeconomics..."):
        # Add user message to history and display it
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get LLM response
        with st.spinner("Thinking..."):
            # Pass the entire chat history for context
            response = get_llm_response(st.session_state.chat_history)
        
        # Add assistant response to history and display it
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)
        
        # Log the interaction
        log_interaction(st.session_state.anonymized_user_id, prompt, response)


# --- Main App Router ---
# This logic determines which page to show.
if st.session_state.page == "Landing":
    show_landing_page()
else:
    show_chat_interface()

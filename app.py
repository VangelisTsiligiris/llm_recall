import streamlit as st
import uuid
import json
import datetime
import os
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials

# --- Page Configuration ---
st.set_page_config(
    page_title="Neuroeconomics Learning Study",
    layout="wide"
)

# --- Authentication and Clients ---
# Authenticate with OpenAI using Streamlit Secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("OpenAI API key is not set in Streamlit Secrets. Please add it and reboot the app.")
    st.stop()

# Authenticate with Google Sheets using Streamlit Secrets
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(creds)
    # *** IMPORTANT: UPDATE THIS WITH THE EXACT NAME OF YOUR GOOGLE SHEET ***
    gsheet = gc.open("LLM Recall Study Logs").sheet1
except Exception as e:
    st.error(f"Failed to connect to Google Sheets. Please ensure your 'gcp_service_account' secret is configured correctly. Error: {e}")
    st.stop()


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

# --- MODIFIED FUNCTION ---
def log_interaction(user_id, prompt, response):
    """
    Logs a new interaction as a row in the configured Google Sheet.
    """
    try:
        # Create a new row with the interaction data
        row_to_insert = [
            datetime.datetime.now().isoformat(),
            user_id,
            prompt,
            response,
        ]
        gsheet.append_row(row_to_insert)
    except Exception as e:
        # Show an error in the app if logging fails, but don't stop the app
        st.error(f"Failed to log interaction to Google Sheet. Error: {e}")


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
        during a learning task affects the ability to recall knowledge 48 hours later. The findings will help 
        design evidence-based guidance for the effective use of AI tools in education.
        """
    )

    st.subheader("What Will You Be Doing?")
    st.markdown(
        """
        This study is a controlled experiment where you will first engage in independent study of provided materials on the topic of **Neuroeconomics**. 
        Neuroeconomics is an interdisciplinary field that combines neuroscience, economics, and psychology to understand human decision-making.
        
        After the study period, you will complete a series of analytical tasks, including:
        * Analyzing business case studies where decision biases may have been involved.
        * Designing a simple experiment to test a neuroeconomic principle.
        * Developing strategic recommendations based on what you have learned.
        
        Your group has been assigned to use this chat interface to assist you during the application tasks. Every interaction (your prompts and the AI's responses) 
        will be logged for later analysis to see which patterns of use predict better recall.
        """
    )

    st.info(f"Your anonymous participant ID is: **{st.session_state.anonymized_user_id}**\n\nPlease write this ID down. You will need it for the paper-based recall test later.")

    if st.button("Proceed to Chat Interface"):
        st.session_state.page = "Chat"
        st.rerun()


def show_chat_interface():
    """
    Displays the main chat interface for interacting with the LLM.
    """
    st.sidebar.header("About this Study")
    st.sidebar.info(
        """
        This research explores how interacting with an LLM affects knowledge recall. 
        Your anonymous interaction logs are collected to help us understand which usage patterns 
        lead to better learning outcomes.
        """
    )
    st.sidebar.header("Contact Information")
    st.sidebar.markdown(
        """
        **Chief Investigator:**
        Vangelis Tsiligkiris
        
        For any questions or concerns, please contact:
        vangelis.tsiligiris@ntu.ac.uk
        """
    )
    
    st.title("Neuroeconomics Learning Assistant")
    st.markdown(
        """
        Use this interface to ask questions and get help with the application tasks. This assistant is powered by **OpenAI's GPT-4 model** (ChatGPT). 
        Remember, all of your on-screen activity (prompts, timestamps, and model replies) is being recorded automatically.
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
        
        # Log the interaction to Google Sheets
        log_interaction(st.session_state.anonymized_user_id, prompt, response)


# --- Main App Router ---
# This logic determines which page to show.
if st.session_state.page == "Landing":
    show_landing_page()
else:
    show_chat_interface()

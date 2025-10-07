import streamlit as st
import random
import string
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from st_copy_to_clipboard import st_copy_to_clipboard

# --- Page Configuration ---
st.set_page_config(
    page_title="Neuroeconomics Learning Study",
    layout="centered"
)

# --- Authentication and Clients ---
try:
    genai.configure(api_key=st.secrets["google_api"]["gemini_api_key"])
    gemini_model = genai.GenerativeModel('gemma-3-1b-it')
except Exception as e:
    st.error(f"Failed to configure Gemini API. Please check your 'google_api' secrets. Error: {e}")
    st.stop()

try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(creds)
    gsheet = gc.open("LLM Recall Study Logs").sheet1
except Exception as e:
    st.error(f"Failed to connect to Google Sheets. Error: {e}")
    st.stop()

# --- Short ID Generator ---
def generate_short_id(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# --- Streaming Function ---
def get_gemini_response_stream(prompt_parts):
    try:
        for chunk in gemini_model.generate_content(prompt_parts, stream=True):
            yield chunk.text
    except Exception as e:
        yield f"Error calling Gemini API: {str(e)}"

def log_interaction(user_id, turn_count, attachment_type, prompt, response, duration_ms):
    try:
        row_to_insert = [
            datetime.datetime.now().isoformat(),
            user_id,
            turn_count,
            attachment_type,
            prompt,
            response,
            len(prompt),
            len(response) if response else 0,
            round(duration_ms)
        ]
        gsheet.append_row(row_to_insert)
    except Exception as e:
        st.error(f"Failed to log interaction to Google Sheet. Error: {e}")

def format_chat_history_for_download(history):
    formatted_string = "Chat History\n"
    formatted_string += f"Participant ID: {st.session_state.anonymized_user_id}\n"
    formatted_string += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    formatted_string += "="*40 + "\n\n"
    
    for message in history:
        role = "You" if message["role"] == "user" else "AI Assistant"
        text = message.get("text", "")
        formatted_string += f"**{role}:**\n{text}\n\n"
        formatted_string += "---\n\n"
        
    return formatted_string

# --- Session State Initialization ---
if "anonymized_user_id" not in st.session_state:
    st.session_state.anonymized_user_id = generate_short_id()
    st.session_state.chat_history = []
    st.session_state.page = "Landing"
    st.session_state.turn_count = 0

# --- Custom CSS for ChatGPT-like UI ---
st.markdown("""
<style>
    .chat-message {
        padding: 0.8rem 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        max-width: 75%;
        line-height: 1.5;
        font-size: 1rem;
    }
    .chat-message.user {
        background-color: #DCF8C6;
        margin-left: auto;
        text-align: right;
    }
    .chat-message.assistant {
        background-color: #F1F0F0;
        margin-right: auto;
        text-align: left;
    }
    .sidebar .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- Pages ---
def show_landing_page():
    st.title("Welcome to the Neuroeconomics Learning Study")
    st.header("About This Research Project")
    st.markdown(
        """
        You have been invited to participate in a research project that explores how using a Large Language Model (LLM)
        during a learning task affects the ability to recall knowledge later. 

        **Please do not use any other LLM (ChatGPT, Gemini, etc.) or the web during this study. It is important to use only this LLM,
        which is based on Gemini.**

        **Take note of your anonymous ID. Do not close this tab during the entire session.**

        During the study, you will be asked to complete two tasks. For one of the tasks, you will be asked to use the LLM. 
        
        """
    )
    st.info(f"Your anonymous participant ID is: **{st.session_state.anonymized_user_id}**\n\nPlease write this ID down.")
    if st.button("Proceed to Chat Interface"):
        st.session_state.page = "Chat"
        st.rerun()

def show_chat_interface():
    # Sidebar
    with st.sidebar:
        st.header("Resources")
        st.markdown(
            """
            Here you will be able to find the readings for the topic and the templates to complete the tasks
            https://myntuac-my.sharepoint.com/:f:/g/personal/vangelis_tsiligiris_ntu_ac_uk/Eojre-WuJsNMvWRazI-UMEoBllS3gpR0BtTRCfR3NtpfAQ?e=4MhLh9

            """
        )
        st.header("Submit your response to the tasks")
        st.markdown( 
            """
             When you are ready to submit your response to the task, please upload it in this folder :https://myntuac-my.sharepoint.com/:f:/g/personal/vangelis_tsiligiris_ntu_ac_uk/EnoxSOEUDTxJpb60n6-Q7BcB9rCe99a1qgFYbBsbqvn1RA?e=h91hRy
             """
        )
        st.header("Contact Information")
        st.markdown(
            """
            **Principal Investigator:** Vangelis Tsiligkiris  
            vangelis.tsiligiris@ntu.ac.uk            
            """
        )
        st.divider()
        if st.session_state.chat_history:
            st.download_button(
                label="📥 Download Chat History",
                data=format_chat_history_for_download(st.session_state.chat_history),
                file_name=f"chat_history_{st.session_state.anonymized_user_id}.txt",
                mime="text/plain"
            )

    st.title("Google Gemini Learning Assistant")
    st.warning(f"Your Anonymous Participant ID: **{st.session_state.anonymized_user_id}**")
    st.divider()

    # Display chat history with bubbles
    for message in st.session_state.chat_history:
        role = message["role"]
        css_class = "assistant" if role == "assistant" else "user"
        st.markdown(f'<div class="chat-message {css_class}">{message["text"]}</div>', unsafe_allow_html=True)

    # Input field
    if prompt := st.chat_input("Type your question here..."):
        st.session_state.turn_count += 1
        api_prompt_parts = [prompt]

        # Show user message
        st.session_state.chat_history.append({"role": "user", "text": prompt})

        # Get assistant response
        with st.chat_message("assistant"):
            start_time = time.time()
            full_response = st.write_stream(get_gemini_response_stream(api_prompt_parts))
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            st_copy_to_clipboard(full_response, "Copy response")

        st.session_state.chat_history.append({"role": "assistant", "text": full_response})

        # Log
        log_interaction(
            user_id=st.session_state.anonymized_user_id,
            turn_count=st.session_state.turn_count,
            attachment_type="Text Only",
            prompt=prompt,
            response=full_response,
            duration_ms=duration_ms
        )

        st.rerun()

# Router
if st.session_state.page == "Landing":
    show_landing_page()
else:
    show_chat_interface()




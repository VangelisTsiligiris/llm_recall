import streamlit as st
import uuid
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image
from streamlit_copy_button import copy_button

# --- Page Configuration ---
st.set_page_config(
    page_title="Neuroeconomics Learning Study",
    layout="wide"
)

# --- Authentication and Clients ---
try:
    genai.configure(api_key=st.secrets["google_api"]["gemini_api_key"])
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
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

# --- Core Functions ---
def get_gemini_response(prompt_parts):
    try:
        response = gemini_model.generate_content(prompt_parts)
        return response.text
    except Exception as e:
        st.error(f"Error calling Gemini API: {str(e)}")
        return f"Error: {str(e)}"

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

# --- NEW HELPER FUNCTION ---
def format_chat_history_for_download(history):
    """Formats the chat history into a readable string for downloading."""
    formatted_string = "Chat History\n"
    formatted_string += f"Participant ID: {st.session_state.anonymized_user_id}\n"
    formatted_string += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    formatted_string += "="*40 + "\n\n"
    
    for message in history:
        role = "You" if message["role"] == "user" else "AI Assistant"
        text = message.get("text", "[Image attached]")
        formatted_string += f"**{role}:**\n{text}\n\n"
        formatted_string += "---\n\n"
        
    return formatted_string

# --- Session State Initialization ---
if "anonymized_user_id" not in st.session_state:
    st.session_state.anonymized_user_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.page = "Landing"
    st.session_state.turn_count = 0

# --- UI Pages ---
def show_landing_page():
    st.title("Welcome to the Neuroeconomics Learning Study")
    st.header("About This Research Project")
    st.markdown("You have been invited to participate in a research project that explores how using a Large Language Model (LLM) during a learning task affects the ability to recall knowledge 48 hours later.")
    st.info(f"Your anonymous participant ID is: **{st.session_state.anonymized_user_id}**\n\nPlease write this ID down.")
    if st.button("Proceed to Chat Interface"):
        st.session_state.page = "Chat"
        st.rerun()

def show_chat_interface():
    # --- Sidebar ---
    with st.sidebar:
        st.header("About this Study")
        st.info(
            "This research explores how interacting with an LLM affects knowledge recall. Your anonymous interaction logs are collected to help us understand which usage patterns lead to better learning outcomes."
        )
        st.header("Contact Information")
        st.markdown(
            """
            **Chief Investigator:**\n
            Vangelis Tsiligkiris\n
            For any questions or concerns, please contact:\n
            vangelis.tsiligiris@ntu.ac.uk
            """
        )
        st.divider()
        
        # --- NEW: Download Button ---
        if st.session_state.chat_history:
            st.download_button(
                label="📥 Download Chat History",
                data=format_chat_history_for_download(st.session_state.chat_history),
                file_name=f"chat_history_{st.session_state.anonymized_user_id}.txt",
                mime="text/plain"
            )

    # --- Main Chat Interface ---
    st.title("Neuroeconomics Learning Assistant")
    st.markdown("Use this interface to ask questions. This assistant is powered by **Google's Gemini model**.")
    st.warning(f"Your Anonymous Participant ID: **{st.session_state.anonymized_user_id}**")

    st.subheader("📝 Upload a File (Optional)")
    uploaded_file = st.file_uploader("Upload an image to discuss with the AI", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", width=300)

    st.divider()

    st.subheader("🤖 Chat with the AI")
    # Display chat history with copy buttons
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            text = message.get("text", "")
            st.write(text)
            if "image" in message:
                st.image(message["image"], width=200)
            
            # --- NEW: Copy Button ---
            if message["role"] == "assistant" and text:
                copy_button(text, "Copy Response")
    
    # --- Prompt Input and Processing ---
    if prompt := st.chat_input("Ask a question about your upload or the topic..."):
        st.session_state.turn_count += 1
        attachment_type = "Text Only"
        api_prompt_parts = [prompt]
        user_message_to_history = {"role": "user", "text": prompt}

        if uploaded_file is not None:
            attachment_type = "Image Upload"
            img = Image.open(uploaded_file)
            api_prompt_parts.append(img)
            user_message_to_history["image"] = uploaded_file
        
        # Display user message immediately
        with st.chat_message("user"):
            st.write(prompt)
            if uploaded_file is not None:
                 st.image(uploaded_file, width=200)

        # Get and display AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                start_time = time.time()
                response_text = get_gemini_response(api_prompt_parts)
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                st.write(response_text)
                copy_button(response_text, "Copy Response")

        # Update session state history
        st.session_state.chat_history.append(user_message_to_history)
        st.session_state.chat_history.append({"role": "assistant", "text": response_text})
        
        # Log the interaction
        log_interaction(
            user_id=st.session_state.anonymized_user_id,
            turn_count=st.session_state.turn_count,
            attachment_type=attachment_type,
            prompt=prompt,
            response=response_text,
            duration_ms=duration_ms
        )

# --- Main App Router ---
if st.session_state.page == "Landing":
    show_landing_page()
else:
    show_chat_interface()

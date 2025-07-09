import streamlit as st
import uuid
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image
from st_copy_to_clipboard import st_copy_to_clipboard

# --- Page Configuration ---
st.set_page_config(
    page_title="Neuroeconomics Learning Study",
    layout="centered" # Use centered layout for a cleaner look
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

# --- MODIFIED: Core Function for Streaming ---
def get_gemini_response_stream(prompt_parts):
    """
    Yields chunks of the response from the Gemini API.
    """
    try:
        # Use stream=True to get a generator
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
        st.info("This research explores how interacting with an LLM affects knowledge recall.")
        st.header("Contact Information")
        st.markdown(
            """
            **Chief Investigator:** Vangelis Tsiligkiris\n
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

    # --- Main Chat Interface ---
    st.title("Neuroeconomics Learning Assistant")
    st.markdown("This assistant is powered by **Google's Gemini model**.")
    st.warning(f"Your Anonymous Participant ID: **{st.session_state.anonymized_user_id}**")
    
    st.divider()

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            # Display text with Markdown rendering
            st.markdown(message.get("text", ""))
            if "image" in message:
                st.image(message["image"], width=200)

    # --- Prompt Input and Processing ---
    if prompt := st.chat_input("Ask a question about your upload or the topic..."):
        st.session_state.turn_count += 1
        attachment_type = "Text Only"
        api_prompt_parts = [prompt]
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
            # Check for an uploaded file in session state to redisplay
            if "uploaded_file" in st.session_state and st.session_state.uploaded_file is not None:
                st.image(st.session_state.uploaded_file, width=200)

        # Handle file upload if it exists
        if "uploaded_file" in st.session_state and st.session_state.uploaded_file is not None:
            attachment_type = "Image Upload"
            img = Image.open(st.session_state.uploaded_file)
            api_prompt_parts.append(img)
            
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "text": prompt})

        # Get and display AI response using streaming
        with st.chat_message("assistant"):
            start_time = time.time()
            # Use st.write_stream to display the response as it comes in
            full_response = st.write_stream(get_gemini_response_stream(api_prompt_parts))
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Add a copy button for the completed response
            st_copy_to_clipboard(full_response, "Copy response")

        # Add assistant response to history
        st.session_state.chat_history.append({"role": "assistant", "text": full_response})
        
        # Log the interaction
        log_interaction(
            user_id=st.session_state.anonymized_user_id,
            turn_count=st.session_state.turn_count,
            attachment_type=attachment_type,
            prompt=prompt,
            response=full_response,
            duration_ms=duration_ms
        )
        
        # Clear the uploaded file from state after processing
        if "uploaded_file" in st.session_state:
            st.session_state.uploaded_file = None
            
        st.rerun()

    # Move file uploader here to interact with the new logic
    uploaded_file = st.file_uploader("Upload an image (optional)", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file
        st.rerun()

# --- Main App Router ---
if st.session_state.page == "Landing":
    show_landing_page()
else:
    show_chat_interface()

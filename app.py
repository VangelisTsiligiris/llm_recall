import streamlit as st
import uuid
import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Neuroeconomics Learning Study",
    layout="wide"
)

# --- Authentication and Clients ---
# Authenticate with Google Gemini
try:
    genai.configure(api_key=st.secrets["google_api"]["gemini_api_key"])
    gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Use a multimodal model
except Exception as e:
    st.error(f"Failed to configure Gemini API. Please check your 'google_api' secrets. Error: {e}")
    st.stop()

# Authenticate with Google Sheets
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
    """
    Get response from Gemini API, handling multimodal input.
    """
    try:
        response = gemini_model.generate_content(prompt_parts)
        return response.text
    except Exception as e:
        st.error(f"Error calling Gemini API: {str(e)}")
        return f"Error: {str(e)}"

def log_interaction(user_id, turn_count, attachment_type, prompt, response, duration_ms):
    """
    Logs a new interaction with enriched data to the Google Sheet.
    """
    try:
        row_to_insert = [
            datetime.datetime.now().isoformat(),
            user_id,
            turn_count,
            attachment_type,
            prompt,
            response,
            len(prompt),
            len(response),
            round(duration_ms)
        ]
        gsheet.append_row(row_to_insert)
    except Exception as e:
        st.error(f"Failed to log interaction to Google Sheet. Error: {e}")

# --- Session State Initialization ---
if "anonymized_user_id" not in st.session_state:
    st.session_state.anonymized_user_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.page = "Landing"
    st.session_state.turn_count = 0

# --- UI Pages ---
def show_landing_page():
    # This function remains the same as before
    st.title("Welcome to the Neuroeconomics Learning Study")
    st.header("About This Research Project")
    st.markdown("...") # Add your markdown text here
    st.info(f"Your anonymous participant ID is: **{st.session_state.anonymized_user_id}**\n\nPlease write this ID down.")
    if st.button("Proceed to Chat Interface"):
        st.session_state.page = "Chat"
        st.rerun()

def show_chat_interface():
    st.title("Neuroeconomics Learning Assistant")
    st.markdown("Use this interface to ask questions. This assistant is powered by **Google's Gemini model**.")
    st.warning(f"Your Anonymous Participant ID: **{st.session_state.anonymized_user_id}**")
    
    # --- Main App Layout ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📝 Your Workspace")
        
        # File Uploader
        uploaded_file = st.file_uploader("Upload an image (optional)", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Image")

        # Drawing Canvas
        st.write("Or draw something:")
        canvas_result = st_canvas(
            stroke_width=3,
            stroke_color="#FFFFFF",
            background_color="#000000",
            height=200,
            width=400,
            drawing_mode="freedraw",
            key="canvas",
        )

    with col2:
        st.subheader("🤖 Chat with the AI")
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                if "text" in message:
                    st.write(message["text"])
                if "image" in message:
                    st.image(message["image"])

    # --- Prompt Input and Processing ---
    if prompt := st.chat_input("Ask a question about your upload, drawing, or the topic..."):
        st.session_state.turn_count += 1
        attachment_type = "Text Only"
        prompt_parts = [prompt]

        # --- Handle Attachments ---
        # Prioritize uploaded file over canvas if both exist
        attachment = None
        if uploaded_file is not None:
            attachment = Image.open(uploaded_file)
            attachment_type = "Image Upload"
        elif canvas_result.image_data is not None:
            # Convert canvas data to an image
            img_data = canvas_result.image_data.tobytes()
            attachment = Image.open(io.BytesIO(img_data))
            attachment_type = "Canvas Drawing"

        # Update chat history and prompt parts for API
        user_message = {"role": "user", "text": prompt}
        if attachment:
            prompt_parts.append(attachment)
            user_message["image"] = attachment
        
        st.session_state.chat_history.append(user_message)
        
        # Rerun to display the user's new message immediately
        st.rerun()

    # --- Generate and Display Response ---
    # Check if the last message was from the user to avoid re-running on redraw
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        last_user_message = st.session_state.chat_history[-1]
        
        # Reconstruct prompt parts from the last message
        last_prompt = last_user_message.get("text", "")
        last_attachment = last_user_message.get("image")
        api_prompt_parts = [last_prompt]
        if last_attachment:
            api_prompt_parts.append(last_attachment)
            
        attachment_type_for_log = "Text Only"
        if last_attachment:
            # Simple check if the image came from canvas or upload for logging
            if uploaded_file:
                 attachment_type_for_log = "Image Upload"
            else:
                 attachment_type_for_log = "Canvas Drawing"

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                start_time = time.time()
                response_text = get_gemini_response(api_prompt_parts)
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                st.write(response_text)
        
        # Log the interaction
        log_interaction(
            user_id=st.session_state.anonymized_user_id,
            turn_count=st.session_state.turn_count,
            attachment_type=attachment_type_for_log,
            prompt=last_prompt,
            response=response_text,
            duration_ms=duration_ms
        )

        # Add assistant response to history
        st.session_state.chat_history.append({"role": "assistant", "text": response_text})
        
        # A final rerun to lock the state after the assistant has replied.
        st.rerun()


# --- Main App Router ---
if st.session_state.page == "Landing":
    show_landing_page()
else:
    show_chat_interface()

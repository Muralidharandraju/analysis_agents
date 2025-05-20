import streamlit as st
import requests
import io

# --- Configuration ---
FASTAPI_BASE_URL = "http://localhost:8090" # Replace with your FastAPI server URL
UPLOAD_ENDPOINT = f"{FASTAPI_BASE_URL}/upload_files/"
CHAT_ENDPOINT = f"{FASTAPI_BASE_URL}/analyze_data/"

# --- Helper Functions ---
def upload_files_to_backend(uploaded_files):
    """Sends files to the FastAPI backend."""
    if not uploaded_files:
        return None

    files_to_send = []
    for uploaded_file in uploaded_files:
        # To send a file, we need its name and a file-like object
        files_to_send.append(('files', (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)))

    try:
        response = requests.post(UPLOAD_ENDPOINT, files=files_to_send)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error uploading files: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.error(f"Backend response: {e.response.json()}")
            except ValueError:
                st.error(f"Backend response: {e.response.text}")
        return None

def send_chat_message_to_backend(message, session_id=None, file_ids=None):
    """Sends a chat message to the FastAPI backend."""
    payload = {"query": message}
    if session_id:
        payload["session_id"] = session_id
    if file_ids: # Alternatively, you might pass file_ids if your backend uses them directly
        payload["file_ids"] = file_ids

    try:
        response = requests.post(CHAT_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error sending message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                st.error(f"Backend response: {e.response.json()}")
            except ValueError:
                st.error(f"Backend response: {e.response.text}")
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="Chat with Your Files", layout="wide")
st.title("📄 Chat with Your Uploaded Files")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "uploaded_file_names" not in st.session_state:
    st.session_state.uploaded_file_names = []

with st.sidebar:
    st.header("Upload Files")
    uploaded_files = st.file_uploader(
        "Upload your documents (CSV.)",
        type=['csv' ], # Add more types as supported by your backend
        accept_multiple_files=True,
        key="file_uploader"
    )

    if uploaded_files:
        if st.button("Process Uploaded Files"):
            with st.spinner("Processing files..."):
                upload_response = upload_files_to_backend(uploaded_files)
                if upload_response:
                    st.session_state.session_id = upload_response.get("session_id")
                    # Store names of successfully processed files if backend provides them
                    st.session_state.uploaded_file_names = [f.name for f in uploaded_files]
                    st.success(upload_response.get("message", "Files processed successfully!"))
                    if st.session_state.session_id:
                        st.info(f"Session ID: {st.session_state.session_id}")
                else:
                    st.error("File processing failed. Check error messages above.")

    if st.session_state.uploaded_file_names:
        st.subheader("Active Files:")
        for name in st.session_state.uploaded_file_names:
            st.markdown(f"- {name}")
    elif st.session_state.session_id: # If session_id exists but no files shown, means they were processed in a previous run
        st.info("Files have been processed in this session.")


st.header("Chat Interface")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your documents..."):
    if not st.session_state.session_id and not st.session_state.uploaded_file_names:
        st.warning("Please upload and process files before chatting.")
    else:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response
        with st.spinner("Thinking..."):
            # Pass session_id to backend. Backend associates this with the uploaded files.
            backend_response = send_chat_message_to_backend(prompt, session_id=st.session_state.session_id)
            if backend_response and "response" in backend_response:
                response_text = backend_response["response"]
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                with st.chat_message("assistant"):
                    st.markdown(response_text)
            elif backend_response and "error" in backend_response:
                st.error(f"Error from backend: {backend_response['error']}")
            else:
                st.error("Failed to get a response from the backend.")
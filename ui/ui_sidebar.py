import streamlit as st
import uuid
import os


def initialize_session_state():
    """Initialize all required session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "bot_session" not in st.session_state:
        st.session_state.bot_session = None
    if "conversation_generator" not in st.session_state:
        st.session_state.conversation_generator = None
    if "awaiting_input" not in st.session_state:
        st.session_state.awaiting_input = None
    if "conversation_active" not in st.session_state:
        st.session_state.conversation_active = False
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()


def render_session_stats():
    """Render session statistics"""
    st.markdown("### 📊 Session Information")
    
    message_count = len(st.session_state.messages)
    user_messages = len(
        [m for m in st.session_state.messages if m["role"] == "user"])
    bot_messages = len(
        [m for m in st.session_state.messages if m["role"] == "assistant"])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Messages", message_count)
        st.metric("Your Questions", user_messages)
    with col2:
        st.metric("Bot Responses", bot_messages)
        st.metric("Session ID", st.session_state.session_id)


def render_control_buttons():
    """Render control buttons for clearing conversation and exporting"""
    st.markdown("### 🎛️ Controls")

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.bot_session = None
        st.session_state.conversation_generator = None
        st.session_state.awaiting_input = None
        st.session_state.conversation_active = False
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()

    if st.button("💾 Export Conversation", use_container_width=True,
                 disabled=len(st.session_state.messages) == 0):
        conversation_text = ""
        for message in st.session_state.messages:
            role = "You" if message["role"] == "user" else "HealthBot"
            conversation_text += f"{role}: {message['content']}\n\n"

        st.download_button(
            label="📄 Download as Text",
            data=conversation_text,
            file_name=f"healthbot_conversation_"
                      f"{st.session_state.session_id}.txt",
            mime="text/plain",
            use_container_width=True
        )


def handle_file_upload():
    """Handle PDF file uploads"""
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type="pdf",
        help="Upload PDF files to add them to the knowledge base",
        label_visibility="collapsed",
        accept_multiple_files=True
    )

    if uploaded_files is not None and len(uploaded_files) > 0:
        # Check if we have new files to process
        current_files = {f.name for f in uploaded_files}
        new_files = current_files - st.session_state.processed_files

        if new_files:
            # Save files to health_pdfs directory (overwrite if exists)
            os.makedirs("health_pdfs", exist_ok=True)

            uploaded_count = 0
            for uploaded_file in uploaded_files:
                if uploaded_file.name in new_files:
                    file_path = f"health_pdfs/{uploaded_file.name}"

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Add to session state if not already there
                    file_names = [f["name"] for f in
                                  st.session_state.uploaded_files]
                    if uploaded_file.name not in file_names:
                        st.session_state.uploaded_files.append({
                            "name": uploaded_file.name,
                            "path": file_path
                        })

                    uploaded_count += 1

            # Update processed files
            st.session_state.processed_files.update(new_files)

            if uploaded_count == 1:
                st.success(f"✅ Uploaded {list(new_files)[0]}")
            elif uploaded_count > 1:
                st.success(f"✅ Uploaded {uploaded_count} files")
            st.rerun()


def render_document_library():
    """Render the document library section"""
    st.markdown("### 📄 Document Library")
    
    handle_file_upload()
    
    # Display all available documents
    all_documents = []

    # Add uploaded files
    for file_info in st.session_state.uploaded_files:
        all_documents.append(file_info['name'])

    # Add existing PDF files from health_pdfs folder
    if os.path.exists("health_pdfs"):
        existing_pdfs = [f for f in os.listdir("health_pdfs") 
                         if f.endswith('.pdf')]
        for pdf in existing_pdfs:
            if pdf not in all_documents:  # Avoid duplicates
                all_documents.append(pdf)

    if all_documents:
        st.markdown("**Available Documents:**")
        for doc in sorted(all_documents):  # Sort alphabetically
            st.markdown(f"📄 {doc}")
    else:
        st.info("No documents uploaded yet")


def render_help_section():
    """Render the help section"""
    with st.expander("❓ How to Use HealthBot"):
        st.markdown("""
        1. **Ask a health question** in the chat input below
        2. **HealthBot will research** your topic using web search
        3. **Review the summary** and choose whether to take a quiz
        4. **Answer quiz questions** to test your understanding
        5. **Ask follow-up questions** or explore new topics
        
        **Example questions:**
        - "What are the benefits of meditation?"
        - "How does exercise affect mental health?"
        - "What foods help boost immunity?"
        """)


def render_sidebar():
    """Render the complete sidebar"""
    with st.sidebar:
        initialize_session_state()
        render_session_stats()
        render_control_buttons()
        st.markdown("---")
        render_document_library()
        render_help_section()
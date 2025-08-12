import streamlit as st
import uuid
from typing import Generator
from health_bot import HealthBotSession, UserInputRequest

# Page configuration
st.set_page_config(
    page_title="HealthBot",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTitle {
        text-align: center;
        color: #2E8B57;
        font-size: 3rem;
        margin-bottom: 2rem;
    }
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
    }
    .user-message {
        background-color: #E8F4FD;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .assistant-message {
        background-color: #F0F8F0;
        padding: 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border-left: 4px solid #2E8B57;
    }
    .sidebar-content {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .stats-container {
        display: flex;
        justify-content: space-around;
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .stat-item {
        text-align: center;
    }
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1 class='stTitle'>🏥 HealthBot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666; font-size: 1.2rem; margin-bottom: 2rem;'>Your AI-powered health research assistant</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Session Information")
    
    # Initialize session state
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
    
    # Session stats
    message_count = len(st.session_state.messages)
    user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
    bot_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Messages", message_count)
        st.metric("Your Questions", user_messages)
    with col2:
        st.metric("Bot Responses", bot_messages)
        st.metric("Session ID", st.session_state.session_id)
    
    # Control buttons
    st.markdown("### 🎛️ Controls")
    
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.bot_session = None
        st.session_state.conversation_generator = None
        st.session_state.awaiting_input = None
        st.session_state.conversation_active = False
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    if st.button("💾 Export Conversation", use_container_width=True, disabled=len(st.session_state.messages) == 0):
        conversation_text = ""
        for message in st.session_state.messages:
            role = "You" if message["role"] == "user" else "HealthBot"
            conversation_text += f"{role}: {message['content']}\n\n"
        
        st.download_button(
            label="📄 Download as Text",
            data=conversation_text,
            file_name=f"healthbot_conversation_{st.session_state.session_id}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    # Help section
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

def create_conversation_generator(question: str) -> Generator:
    """Create and start a conversation generator for the given question"""
    bot_session = HealthBotSession(question)
    st.session_state.bot_session = bot_session
    return bot_session.run_conversation()

def continue_conversation(user_input=None):
    """Continue the bot conversation, handling both messages and input requests"""
    try:
        if user_input is not None:
            # Send user response to the generator
            result = st.session_state.conversation_generator.send(user_input)
        else:
            # Get next item from generator
            result = next(st.session_state.conversation_generator)

        if isinstance(result, UserInputRequest):
            # Bot is requesting user input
            st.session_state.awaiting_input = result
        else:
            # Bot sent a message - add it to messages
            st.session_state.messages.append({"role": "assistant", "content": result})
            st.session_state.awaiting_input = None
            
            # Continue processing to get any immediate follow-up messages
            try:
                next_result = next(st.session_state.conversation_generator)
                if isinstance(next_result, UserInputRequest):
                    st.session_state.awaiting_input = next_result
                else:
                    # Another immediate message from bot
                    st.session_state.messages.append({"role": "assistant", "content": next_result})
                    # Check for another input request
                    try:
                        follow_up = next(st.session_state.conversation_generator)
                        if isinstance(follow_up, UserInputRequest):
                            st.session_state.awaiting_input = follow_up
                    except StopIteration:
                        st.session_state.conversation_active = False
            except StopIteration:
                st.session_state.conversation_active = False

    except StopIteration:
        # Conversation ended
        st.session_state.conversation_active = False
        st.session_state.conversation_generator = None
        st.session_state.awaiting_input = None

# Main chat interface
chat_container = st.container()

with chat_container:
    # Display chat history
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    else:
        # Welcome message for new users
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome to HealthBot!** 
            
            I'm here to help you research health topics using the latest information from the web. 
            I can:
            - 🔍 Search for current health information
            - 📝 Provide detailed summaries with citations
            - 🧠 Create quizzes to test your understanding
            - 💬 Answer follow-up questions
            
            **What health topic would you like to explore today?**
            """)

# Handle new user input
if prompt := st.chat_input(
    "Ask a health question...", 
    disabled=st.session_state.awaiting_input is not None
):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Start new conversation or continue existing one
    if not st.session_state.conversation_active:
        st.session_state.conversation_generator = create_conversation_generator(prompt)
        st.session_state.conversation_active = True
    
    # Show loading spinner
    with st.chat_message("assistant"):
        with st.spinner("🔍 Researching your question..."):
            continue_conversation()
    
    st.rerun()

# Handle pending input requests
if st.session_state.awaiting_input:
    input_req = st.session_state.awaiting_input
    
    # Display the bot's request
    with st.chat_message("assistant"):
        st.markdown(input_req.prompt)
    
    # Create appropriate input widget
    if input_req.options:
        # Multiple choice input
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            choice = st.radio(
                "Choose your response:",
                input_req.options,
                key=f"choice_{input_req.input_type}",
                horizontal=True
            )
            
            if st.button("Submit Choice", use_container_width=True, type="primary"):
                # Add user's choice to message history for certain types
                if input_req.input_type in ["new_topic_choice", "quiz_choice"]:
                    st.session_state.messages.append({"role": "user", "content": choice})
                
                continue_conversation(choice)
                st.rerun()
    
    else:
        # Free text input
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if input_req.input_type == "new_question":
                answer = st.text_input(
                    "Enter your new health topic:",
                    key=f"input_{input_req.input_type}",
                    placeholder="e.g., benefits of yoga, healthy diet tips..."
                )
            elif input_req.input_type == "quiz_answer":
                answer = st.text_area(
                    "Your answer:",
                    key=f"input_{input_req.input_type}",
                    placeholder="Type your answer here...",
                    height=100
                )
            else:
                answer = st.text_area(
                    "Your response:",
                    key=f"input_{input_req.input_type}",
                    placeholder="Type your response here...",
                    height=100
                )
            
            if st.button("Submit Response", use_container_width=True, type="primary", disabled=not answer.strip()):
                # Add user's response to message history
                st.session_state.messages.append({"role": "user", "content": answer.strip()})
                
                with st.spinner("Processing your response..."):
                    continue_conversation(answer.strip())
                st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #888; font-size: 0.9rem;'>"
    "⚠️ <strong>Disclaimer:</strong> This bot provides information for educational purposes only. "
    "Always consult with qualified healthcare professionals for medical advice."
    "</p>",
    unsafe_allow_html=True
)
import streamlit as st
from langgraph.graph import END

from health_bot import create_health_bot_graph
from health_bot_session import HealthBotSession, BotResponse
from ui.ui_sidebar import render_sidebar
from ui.ui_styles import (
    configure_page, apply_custom_styles, render_title, render_footer
)

# Configure page and apply styling
configure_page()
apply_custom_styles()
render_title()

# Render sidebar
render_sidebar()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False
if "conversation_generator" not in st.session_state:
    st.session_state.conversation_generator = None
if "awaiting_input" not in st.session_state:
    st.session_state.awaiting_input = None


def start_new_conversation(question: str):
    """Start a new conversation with the given question"""
    graph = create_health_bot_graph()
    bot_session = HealthBotSession(question, graph, END)
    st.session_state.conversation_generator = bot_session.run_conversation()
    st.session_state.conversation_active = True
    st.session_state.awaiting_input = None


def process_bot_response(response: BotResponse):
    """Process a BotResponse and update the UI state accordingly"""
    if response.user_input_request:
        # Bot is requesting user input - add question to chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.user_input_request.prompt
        })
        st.session_state.awaiting_input = response.user_input_request

    elif response.message:
        # Bot sent a message - add it to messages with source info
        message_content = response.message

        # Add source information if available
        if response.information_source:
            source_icons = {
                "rag": "📚",
                "knowledge": "🧠",
                "web": "🔍",
                "documents": "📄"
            }
            icon = source_icons.get(response.information_source, "ℹ️")
            source_text = response.information_source.title()
            message_content = (f"{message_content}\n\n*{icon} Source: "
                               f"{source_text}*")

        st.session_state.messages.append({
            "role": "assistant",
            "content": message_content
        })
        # Clear awaiting input when we get a regular message
        st.session_state.awaiting_input = None


def get_next_bot_response(user_input=None):
    """Get the next response from the bot generator"""
    try:
        if user_input is not None:
            return st.session_state.conversation_generator.send(user_input)
        else:
            return next(st.session_state.conversation_generator)
    except StopIteration:
        # Conversation ended
        st.session_state.conversation_active = False
        st.session_state.conversation_generator = None
        st.session_state.awaiting_input = None
        return None


# Main chat interface
chat_container = st.container()

with chat_container:
    # Display chat history if there's any, otherwise a welcome message
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    else:
        # Welcome message for new users
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome to HealthBot!** 
            
            I'm here to help you research health topics using the latest 
            information from the web. 
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

    # Start new conversation
    if not st.session_state.conversation_active:
        start_new_conversation(prompt)

    # Show loading spinner and process bot responses
    with st.chat_message("assistant"):
        with st.spinner("🔍 Researching your question..."):
            while True:
                response = get_next_bot_response()
                if response is None:
                    break
                process_bot_response(response)
                if response.user_input_request:
                    break

    st.rerun()

# Handle pending input requests
if st.session_state.awaiting_input:
    input_req = st.session_state.awaiting_input

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

            if st.button("Submit Choice", use_container_width=True,
                         type="primary"):
                # Add user's choice to message history for certain types
                if input_req.input_type in ["new_topic_choice", "quiz_choice"]:
                    st.session_state.messages.append(
                        {"role": "user", "content": choice})

                # Process responses until we get another input request or end
                while True:
                    response = get_next_bot_response(
                        choice) if choice else get_next_bot_response()
                    choice = None  # Only send choice on first iteration
                    if response is None:
                        break
                    process_bot_response(response)
                    if response.user_input_request:
                        break
                st.rerun()

    else:
        # Free text input
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with ((((col2)))):
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

            if st.button("Submit Response", use_container_width=True,
                         type="primary", disabled=not answer.strip()):
                # Add user's response to message history
                st.session_state.messages.append(
                    {"role": "user", "content": answer.strip()})

                with st.spinner("Processing your response..."):
                    # Process responses until we get another input request
                    # or end
                    user_input = answer.strip()
                    while True:
                        response = get_next_bot_response(
                            user_input) if user_input \
                            else get_next_bot_response()

                        user_input = None  # Only send input on first iteration
                        if response is None:
                            break
                        process_bot_response(response)
                        if response.user_input_request:
                            break
                st.rerun()

# Footer
render_footer()

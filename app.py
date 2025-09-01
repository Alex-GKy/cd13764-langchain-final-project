import streamlit as st
from typing import Generator
from health_bot_session import HealthBotSession, BotResponse
from health_bot import create_health_bot_graph
from langgraph.graph import END
from ui.ui_styles import configure_page, apply_custom_styles, render_title, render_footer
from ui.ui_sidebar import render_sidebar

# Configure page and apply styling
configure_page()
apply_custom_styles()
render_title()

# Render sidebar
render_sidebar()


def create_conversation_generator(question: str) -> Generator:
    """Create and start a conversation generator for the given question"""
    graph = create_health_bot_graph()
    bot_session = HealthBotSession(question, graph, END)
    st.session_state.bot_session = bot_session
    return bot_session.run_conversation()


def continue_conversation(user_input=None):
    """Continue the bot conversation, handling BotResponse objects"""
    try:
        if user_input is not None:
            # Send user response to the generator
            result = st.session_state.conversation_generator.send(user_input)
        else:
            # Get next item from generator
            result = next(st.session_state.conversation_generator)

        # Handle BotResponse objects
        if isinstance(result, BotResponse):
            if result.user_input_request:
                # Bot is requesting user input - add question to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": result.user_input_request.prompt
                })
                st.session_state.awaiting_input = result.user_input_request
            elif result.message:
                # Bot sent a message - add it to messages with source info
                message_content = result.message
                
                # Add source information if available
                if result.information_source:
                    source_icons = {
                        "rag": "📚",
                        "knowledge": "🧠", 
                        "web": "🔍",
                        "documents": "📄"
                    }
                    icon = source_icons.get(result.information_source, "ℹ️")
                    message_content = f"{message_content}\n\n*{icon} Source: {result.information_source.title()}*"
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": message_content
                })
                st.session_state.awaiting_input = None
                
                # Continue to get any follow-up input requests
                try:
                    next_result = next(st.session_state.conversation_generator)
                    if (isinstance(next_result, BotResponse) and 
                            next_result.user_input_request):
                        # Add the question to chat history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": next_result.user_input_request.prompt
                        })
                        st.session_state.awaiting_input = next_result.user_input_request
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

    # Start new conversation or continue existing one
    if not st.session_state.conversation_active:
        st.session_state.conversation_generator = (
            create_conversation_generator(prompt))
        st.session_state.conversation_active = True

    # Show loading spinner
    with st.chat_message("assistant"):
        with st.spinner("🔍 Researching your question..."):
            continue_conversation()

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

            if st.button("Submit Response", use_container_width=True,
                         type="primary", disabled=not answer.strip()):
                # Add user's response to message history
                st.session_state.messages.append(
                    {"role": "user", "content": answer.strip()})

                with st.spinner("Processing your response..."):
                    continue_conversation(answer.strip())
                st.rerun()

# Footer
render_footer()

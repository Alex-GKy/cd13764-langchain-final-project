import streamlit as st
import os

# Set up API key
if "VOCAREUM_API_KEY" in st.secrets and "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets["VOCAREUM_API_KEY"]

from health_bot import streamlit_health_bot, UserInputRequest

st.title("HealthBot")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "bot_generator" not in st.session_state:
    st.session_state.bot_generator = None
if "awaiting_input" not in st.session_state:
    st.session_state.awaiting_input = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def continue_bot_conversation(user_input=None):
    """Continue the bot conversation, handling both messages and input requests"""
    
    try:
        if user_input is not None:
            # Send user response to the generator
            result = st.session_state.bot_generator.send(user_input)
        else:
            # Get next item from generator
            result = next(st.session_state.bot_generator)

        if isinstance(result, UserInputRequest):
            # Bot is requesting user input
            st.session_state.awaiting_input = result
        else:
            # Bot sent a message
            st.session_state.messages.append({"role": "assistant", "content": result})
            st.session_state.awaiting_input = None
            
            # Continue processing without recursion - let Streamlit handle the rerun
            while True:
                try:
                    next_result = next(st.session_state.bot_generator)
                    if isinstance(next_result, UserInputRequest):
                        st.session_state.awaiting_input = next_result
                        break
                    else:
                        # Another message from bot
                        st.session_state.messages.append({"role": "assistant", "content": next_result})
                except StopIteration:
                    # Conversation ended
                    st.session_state.bot_generator = None
                    st.session_state.awaiting_input = None
                    break

    except StopIteration:
        # Conversation ended
        st.session_state.bot_generator = None
        st.session_state.awaiting_input = None


# Handle new user input
if prompt := st.chat_input("Ask a health question", 
                          disabled=st.session_state.awaiting_input is not None):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Start new bot conversation
    st.session_state.bot_generator = streamlit_health_bot(prompt)
    continue_bot_conversation()
    st.rerun()

# Handle pending input requests
if st.session_state.awaiting_input:
    input_req = st.session_state.awaiting_input
    
    with st.chat_message("assistant"):
        st.markdown(input_req.prompt)
    
    if input_req.options:
        # Multiple choice
        with st.form(f"form_{input_req.input_type}", clear_on_submit=True):
            choice = st.radio("Choose an option:", input_req.options, index=0)
            if st.form_submit_button("Submit"):
                continue_bot_conversation(choice)
                st.rerun()
    else:
        # Free text input
        with st.form(f"form_{input_req.input_type}", clear_on_submit=True):
            answer = st.text_area("Your response:")
            if st.form_submit_button("Submit") and answer.strip():
                continue_bot_conversation(answer.strip())
                st.rerun()
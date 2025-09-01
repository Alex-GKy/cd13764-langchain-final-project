import streamlit as st


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="HealthBot",
        page_icon="🏥",
        layout="centered",
        initial_sidebar_state="expanded"
    )


def apply_custom_styles():
    """Apply custom CSS styling to the Streamlit app"""
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


def render_title():
    """Render the main title and subtitle"""
    st.markdown("<h1 class='stTitle'>🏥 HealthBot</h1>", 
                unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #666; font-size: 1.2rem; "
        "margin-bottom: 2rem;'>Your AI-powered health research assistant</p>",
        unsafe_allow_html=True)


def render_footer():
    """Render the footer disclaimer"""
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888; font-size: 0.9rem;'>"
        "⚠️ <strong>Disclaimer:</strong> This bot provides information for "
        "educational purposes only. "
        "Always consult with qualified healthcare professionals for medical "
        "advice."
        "</p>",
        unsafe_allow_html=True
    )
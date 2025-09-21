"""
Main VoiceBot application using modular components.
This is the entry point for the Streamlit application.
"""

import streamlit as st
from groq import Groq
from streamlit_ui import StreamlitUI
from config import GROQ_MODEL_TEXT, GROQ_MODEL_STT, GROQ_MODEL_TTS, GROQ_TTS_VOICE


def main():
    """Main application entry point."""
    # Configure APIs
    groq_available = False
    groq_client = None
    deepgram_available = False

    try:
        groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        groq_available = True
    except Exception as e:
        groq_available = False

    # Check Deepgram API availability
    try:
        deepgram_api_key = st.secrets.get("DEEPGRAM_API_KEY")
        if deepgram_api_key:
            deepgram_available = True
    except Exception as e:
        deepgram_available = False

    # Check if at least one TTS service is available
    if not groq_available and not deepgram_available:
        st.error("❌ No TTS services configured. Please add GROQ_API_KEY or DEEPGRAM_API_KEY to your secrets.")
    elif not groq_available:
        st.warning("⚠️ Groq API is not configured. Using Deepgram TTS as fallback.")
    elif not deepgram_available:
        st.info("ℹ️ Deepgram API is not configured. Only Groq TTS will be available.")

    # Model configuration
    model_config = {
        "text": st.secrets.get("GROQ_MODEL_TEXT", GROQ_MODEL_TEXT),
        "stt": st.secrets.get("GROQ_MODEL_STT", GROQ_MODEL_STT),
        "tts": st.secrets.get("GROQ_MODEL_TTS", GROQ_MODEL_TTS),
        "voice": st.secrets.get("GROQ_TTS_VOICE", GROQ_TTS_VOICE),
        "deepgram_available": deepgram_available
    }

    # Initialize and run the UI
    if groq_client or deepgram_available:
        ui = StreamlitUI(groq_client)
        ui.run(groq_available, model_config)
    else:
        # Show error state if no API client
        st.error("❌ Unable to initialize application. Please check your API configuration.")


if __name__ == "__main__":
    main()

"""
Text-to-Speech service for the VoiceBot application.
Handles speech generation using Groq's PlayAI TTS API with Deepgram fallback.
"""

import tempfile
import base64
import streamlit as st
from groq import Groq
from deepgram import DeepgramClient, SpeakOptions
from config import GROQ_MODEL_TTS, GROQ_TTS_VOICE, DEEPGRAM_TTS_MODEL


class TTSService:
    """Handles text-to-speech conversion using Groq's PlayAI TTS API with Deepgram fallback."""
    
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.model = GROQ_MODEL_TTS
        self.voice = GROQ_TTS_VOICE
        
        # Initialize Deepgram client for fallback
        self.deepgram_client = None
        try:
            deepgram_api_key = st.secrets.get("DEEPGRAM_API_KEY")
            if deepgram_api_key:
                self.deepgram_client = DeepgramClient(deepgram_api_key)
        except Exception as e:
            st.warning(f"Deepgram API key not configured: {e}")
            self.deepgram_client = None

    def generate_speech(self, text):
        """Generate speech from text using Groq PlayAI TTS with Deepgram fallback."""
        # Try Groq PlayAI TTS first
        try:
            # Generate speech using Groq PlayAI TTS
            response = self.groq_client.audio.speech.create(
                model=self.model,
                input=text,
                voice=self.voice,  # Configurable voice
                response_format="mp3"
            )
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                # Read the response content
                audio_data = response.read()
                tmp_file.write(audio_data)
                return tmp_file.name
                
        except Exception as e:
            # Check if it's a terms acceptance error
            if "terms acceptance" in str(e).lower():
                st.warning("⚠️ Groq PlayAI TTS requires terms acceptance. Using Deepgram TTS instead...")
            elif "rate limit" in str(e).lower() or "429" in str(e):
                st.warning("⚠️ Groq TTS rate limit reached. Using Deepgram TTS instead...")
            else:
                st.warning("⚠️ Groq TTS temporarily unavailable. Using Deepgram TTS instead...")
            
            # Fallback to Deepgram TTS
            return self.generate_speech_deepgram(text)
    
    def generate_speech_deepgram(self, text):
        """Generate speech from text using Deepgram TTS as fallback."""
        if not self.deepgram_client:
            st.error("❌ Deepgram API key not configured. Please add DEEPGRAM_API_KEY to your secrets.")
            return None
            
        try:
            # Prepare text for Deepgram
            text_data = {"text": text}
            
            # Configure Deepgram options
            options = SpeakOptions(
                model=DEEPGRAM_TTS_MODEL,
            )
            
            # Generate speech using Deepgram
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                response = self.deepgram_client.speak.v("1").save(
                    tmp_file.name,
                    text_data,
                    options,
                )
                
                # Check if the file was created successfully
                import os
                if os.path.exists(tmp_file.name) and os.path.getsize(tmp_file.name) > 0:
                    st.success("✅ Speech generated using Deepgram TTS")
                    return tmp_file.name
                else:
                    st.error("❌ Deepgram TTS failed to generate audio file")
                    return None
                    
        except Exception as e:
            st.error(f"❌ Deepgram TTS failed: {e}")
            return None

    def play_audio_file(self, audio_file_path):
        """Play audio file in Streamlit."""
        try:
            with open(audio_file_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
                st.audio(audio_bytes, format="audio/mp3")
        except Exception as e:
            st.error(f"Error playing audio: {str(e)}")

    def play_audio_immediately(self, audio_file_path):
        """Play audio file immediately with JavaScript autoplay."""
        try:
            with open(audio_file_path, "rb") as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode()
                
                # Create audio element with immediate playback
                st.markdown(f"""
                <audio controls autoplay style="width: 100%; margin: 10px 0;">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    Your browser does not support the audio element.
                </audio>
                <script>
                // Force play the audio immediately
                setTimeout(function() {{
                    const audio = document.querySelector('audio[src*="{audio_base64[:20]}"]');
                    if (audio) {{
                        audio.play().catch(e => {{
                            console.log('Autoplay prevented:', e);
                            // Create a prominent play button if autoplay fails
                            const playBtn = document.createElement('button');
                            playBtn.innerHTML = '🔊 Click to Play Response';
                            playBtn.style.cssText = 'background: #ff6b6b; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; margin: 10px 0; width: 100%;';
                            playBtn.onclick = () => audio.play();
                            audio.parentNode.insertBefore(playBtn, audio.nextSibling);
                        }});
                    }}
                }}, 100);
                </script>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error playing audio immediately: {str(e)}")

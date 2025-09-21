"""
Speech-to-Text service for the VoiceBot application.
Handles audio transcription using Groq's Whisper API.
"""

import io
import numpy as np
import soundfile as sf
import streamlit as st
from groq import Groq
from config import SAMPLE_RATE, GROQ_MODEL_STT


class STTService:
    """Handles speech-to-text conversion using Groq's Whisper API."""
    
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.model = GROQ_MODEL_STT

    def transcribe_audio_file(self, audio_file_path):
        """Transcribe audio from a file path using Groq Whisper Large v3."""
        try:
            with open(audio_file_path, "rb") as audio_file:
                # Use Groq's Whisper API with English language specification
                response = self.groq_client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="en",  # Force English language
                    response_format="verbose_json"
                )
            return response.text
        except Exception as e:
            st.error(f"Error transcribing audio with Groq: {str(e)}")
            return None

    def transcribe_audio_data(self, audio_data):
        """Transcribe audio data directly from numpy array."""
        try:
            # Normalize audio data
            audio_data = audio_data / np.max(np.abs(audio_data))
            
            # Convert to bytes
            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, audio_data, SAMPLE_RATE, format='WAV')
            audio_bytes.seek(0)
            
            # Use Groq for transcription
            try:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=("recording.wav", audio_bytes.read()),
                    model=self.model,
                    language="en",  # Force English language
                    response_format="verbose_json",
                )
                return transcription.text
            except Exception as e:
                st.error(f"Groq transcription failed: {e}")
                return None
                
        except Exception as e:
            st.error(f"Transcription error: {e}")
            return None

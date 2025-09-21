"""
Language Model service for the VoiceBot application.
Handles text generation using Groq's LLM API.
"""

import streamlit as st
from groq import Groq
from config import GROQ_MODEL_TEXT, SYSTEM_PROMPT


class LLMService:
    """Handles text generation using Groq's language models."""
    
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.model = GROQ_MODEL_TEXT
        self.system_prompt = SYSTEM_PROMPT

    def clean_message_for_api(self, message):
        """Remove UI-specific fields from message for API calls."""
        return {
            "role": message["role"],
            "content": message["content"]
        }

    def generate_response(self, user_message, conversation_history):
        """Generate response using Groq language model."""
        try:
            # Build messages with conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history (filter out input_method field)
            for turn in conversation_history:
                messages.append(self.clean_message_for_api(turn))
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response using Groq
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating response with Groq: {str(e)}")
            return None

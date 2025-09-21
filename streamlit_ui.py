"""
Streamlit UI components and main application logic for the VoiceBot.
Handles conversation management, UI rendering, and user interactions.
"""

import os
import tempfile
import datetime
import streamlit as st
from audio_recorder import AudioRecorder
from stt_service import STTService
from tts_service import TTSService
from llm_service import LLMService
from config import PAGE_CONFIG


class StreamlitUI:
    """Handles all Streamlit UI components and application logic."""
    
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.stt_service = STTService(groq_client)
        self.tts_service = TTSService(groq_client)
        self.llm_service = LLMService(groq_client)
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialize all session state variables."""
        if "conversations" not in st.session_state:
            st.session_state.conversations = []
        if "current_conversation" not in st.session_state:
            st.session_state.current_conversation = []
        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = 0
        if "recording" not in st.session_state:
            st.session_state.recording = False
        if "audio_file" not in st.session_state:
            st.session_state.audio_file = None
        if "audio_recorder" not in st.session_state:
            st.session_state.audio_recorder = AudioRecorder()
        if "audio_files" not in st.session_state:
            st.session_state.audio_files = {}  # Store audio file paths for each message
        if "trigger_immediate_tts" not in st.session_state:
            st.session_state.trigger_immediate_tts = None  # Store text for immediate TTS

    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(**PAGE_CONFIG)

    def add_autoplay_script(self):
        """Add JavaScript for automatic audio playback."""
        st.markdown("""
        <script>
        // Function to automatically play audio when it's added to the page
        function autoPlayAudio() {
            const audioElements = document.querySelectorAll('audio');
            audioElements.forEach(audio => {
                if (!audio.hasAttribute('data-autoplayed')) {
                    audio.setAttribute('data-autoplayed', 'true');
                    audio.play().catch(e => {
                        console.log('Autoplay prevented by browser:', e);
                        // Show a play button if autoplay fails
                        const playButton = document.createElement('button');
                        playButton.innerHTML = '🔊 Play Response';
                        playButton.style.cssText = 'background: #ff6b6b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 5px;';
                        playButton.onclick = () => audio.play();
                        audio.parentNode.insertBefore(playButton, audio.nextSibling);
                    });
                }
            });
        }

        // Run autoplay when page loads
        document.addEventListener('DOMContentLoaded', autoPlayAudio);

        // Run autoplay when new content is added (for Streamlit reruns)
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    setTimeout(autoPlayAudio, 100);
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        </script>
        """, unsafe_allow_html=True)

    def render_sidebar(self, groq_available, model_config):
        """Render the sidebar with conversation history and controls."""
        with st.sidebar:
            st.title("💬 Chat History")
            
            # API Status
            if groq_available:
                st.success("✅ Groq Connected")
                st.caption(f"Text: {model_config['text']}")
                st.caption(f"STT: {model_config['stt']}")
                st.caption(f"TTS: {model_config['tts']}")
                st.caption(f"Voice: {model_config['voice']}")
            else:
                st.error("❌ Groq API Not Connected")
            
            # Deepgram Status
            if model_config.get('deepgram_available', False):
                st.success("✅ Deepgram TTS Available")
                st.caption("Fallback TTS service")
            else:
                st.warning("⚠️ Deepgram TTS Not Configured")
            
            st.divider()
            
            # New Chat button
            if st.button("➕ New Chat", use_container_width=True, key="new_chat_button"):
                self.start_new_conversation()
                st.rerun()
            
            # Cleanup audio files button
            if st.button("🧹 Clean Audio", use_container_width=True, key="cleanup_audio_button"):
                self.cleanup_audio_files()
                st.success("Audio files cleaned up!")
                st.rerun()
            
            st.divider()
            
            # Conversation history
            if st.session_state.conversations:
                st.subheader("Recent Conversations")
                
                for conv in st.session_state.conversations:
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        if st.button(
                            conv["title"], 
                            key=f"load_{conv['id']}",
                            use_container_width=True,
                            help=f"Last message: {conv['timestamp']}"
                        ):
                            self.load_conversation(conv["id"])
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️", key=f"delete_{conv['id']}", help="Delete conversation"):
                            self.delete_conversation(conv["id"])
                            st.rerun()
            else:
                st.info("No conversations yet. Start chatting to see your history here!")

    def render_main_interface(self, groq_available, model_config):
        """Render the main chat interface."""
        # Main chat area
        st.title("🤖 Nitin's Voice Bot")
        st.caption("Ask me anything about my background, experience, or projects! Use voice input only.")

        # TTS Status info
        if groq_available:
            st.info("🔊 **Voice Agent Active**: All responses are automatically spoken immediately using Groq PlayAI TTS!")
        elif model_config.get('deepgram_available', False):
            st.info("🔊 **Voice Agent Active**: All responses are automatically spoken using Deepgram TTS!")
        else:
            st.warning("⚠️ **Voice Agent Unavailable**: TTS requires Groq or Deepgram API key. Voice responses only.")

        # Chat messages container
        chat_container = st.container()

        # Display current conversation
        with chat_container:
            if st.session_state.current_conversation:
                for i, message in enumerate(st.session_state.current_conversation):
                    if message["role"] == "user":
                        with st.chat_message("user"):
                            st.markdown("🎤 **Voice Input**")
                            st.write(message["content"])
                    else:
                        with st.chat_message("assistant"):
                            st.write(message["content"])
                            
                            # Show audio player if audio file exists
                            message_key = f"msg_{i}"
                            if message_key in st.session_state.audio_files:
                                self.tts_service.play_audio_file(st.session_state.audio_files[message_key])
            else:
                # Welcome message
                with st.chat_message("assistant"):
                    st.write("👋 Hi! I'm Nitin, part-time Human and full-time AI Buff. Ask me anything about my background, experience, or projects!")

    def render_immediate_tts_section(self):
        """Render the immediate TTS trigger section."""
        if st.session_state.trigger_immediate_tts:
            with st.spinner("🔊 Generating and playing speech response..."):
                audio_file = self.tts_service.generate_speech(st.session_state.trigger_immediate_tts)
                if audio_file:
                    # Save audio file for conversation history - use the last assistant message index
                    # Find the last assistant message in the conversation
                    last_assistant_index = -1
                    for i in range(len(st.session_state.current_conversation) - 1, -1, -1):
                        if st.session_state.current_conversation[i]["role"] == "assistant":
                            last_assistant_index = i
                            break
                    
                    if last_assistant_index >= 0:
                        message_key = f"msg_{last_assistant_index}"
                        st.session_state.audio_files[message_key] = audio_file
                    
                    # Play audio immediately
                    self.tts_service.play_audio_immediately(audio_file)
                else:
                    st.error("❌ Failed to generate speech. Please check your API configuration.")
            
            # Clear the trigger
            st.session_state.trigger_immediate_tts = None

    def render_voice_input_controls(self):
        """Render voice input controls."""
        st.markdown("---")

        # Voice input controls
        if st.session_state.recording:
            if st.button("⏹️ Stop Recording", type="primary", use_container_width=True, key="stop_recording_visual"):
                if self.stop_voice_recording():
                    st.rerun()
        else:
            if st.button("🎤 Record Voice", type="secondary", use_container_width=True, key="start_voice_recording"):
                self.start_voice_recording()
                st.rerun()

        # Show recording status if recording
        if st.session_state.recording:
            self.render_recording_status()

    def render_recording_status(self):
        """Render the recording status animation."""
        st.markdown("""
        <div style="text-align: center; padding: 10px; border: 2px solid #ff4444; border-radius: 8px; background-color: #fff5f5; margin: 10px 0;">
            <div style="color: #ff4444; font-weight: bold;">🎤 Recording... Speak now!</div>
            <div style="display: flex; justify-content: center; gap: 3px; margin-top: 8px;">
                <div style="width: 3px; height: 15px; background: #ff4444; animation: wave 1s infinite;"></div>
                <div style="width: 3px; height: 20px; background: #ff4444; animation: wave 1s infinite 0.1s;"></div>
                <div style="width: 3px; height: 18px; background: #ff4444; animation: wave 1s infinite 0.2s;"></div>
                <div style="width: 3px; height: 22px; background: #ff4444; animation: wave 1s infinite 0.3s;"></div>
                <div style="width: 3px; height: 15px; background: #ff4444; animation: wave 1s infinite 0.4s;"></div>
            </div>
        </div>
        <style>
        @keyframes wave {
            0%, 100% { height: 15px; }
            50% { height: 25px; }
        }
        </style>
        """, unsafe_allow_html=True)


    def render_footer(self):
        """Render the footer."""
        st.markdown("---")
        st.markdown("Developed by Nitin | nitin.code2@gmail.com")

    def trigger_immediate_tts(self, text):
        """Trigger immediate TTS for the given text."""
        st.session_state.trigger_immediate_tts = text

    def add_assistant_response(self, response):
        """Add assistant response to conversation and trigger TTS."""
        if response:
            st.session_state.current_conversation.append({
                "role": "assistant",
                "content": response
            })
            # Update timestamp
            st.session_state.last_message_time = datetime.datetime.now().strftime("%H:%M")
            
            # Trigger immediate TTS
            self.trigger_immediate_tts(response)
            return True
        return False

    def cleanup_audio_files(self):
        """Clean up temporary audio files."""
        try:
            for message_key, audio_file_path in st.session_state.audio_files.items():
                if os.path.exists(audio_file_path):
                    os.unlink(audio_file_path)
            st.session_state.audio_files = {}
        except Exception as e:
            st.warning(f"Error cleaning up audio files: {str(e)}")

    def save_conversation(self):
        """Save current conversation to history."""
        if st.session_state.current_conversation:
            # Get the first user message for the title
            first_user_message = None
            for message in st.session_state.current_conversation:
                if message["role"] == "user":
                    first_user_message = message
                    break
            
            if first_user_message:
                title = "🎤 " + (first_user_message["content"][:50] + "..." if len(first_user_message["content"]) > 50 else first_user_message["content"])
            else:
                title = "New Conversation"
            
            conversation_data = {
                "id": st.session_state.conversation_id,
                "title": title,
                "messages": st.session_state.current_conversation.copy(),
                "timestamp": st.session_state.get("last_message_time", "Unknown")
            }
            st.session_state.conversations.insert(0, conversation_data)  # Add to top
            st.session_state.conversation_id += 1

    def start_new_conversation(self):
        """Start a new conversation."""
        self.save_conversation()
        st.session_state.current_conversation = []

    def load_conversation(self, conversation_id):
        """Load a conversation from history."""
        for conv in st.session_state.conversations:
            if conv["id"] == conversation_id:
                st.session_state.current_conversation = conv["messages"].copy()
                break

    def delete_conversation(self, conversation_id):
        """Delete a conversation from history."""
        st.session_state.conversations = [conv for conv in st.session_state.conversations if conv["id"] != conversation_id]

    def start_voice_recording(self):
        """Start voice recording."""
        if not st.session_state.recording:
            st.session_state.recording = True
            st.session_state.audio_recorder.start_recording()
            st.success("🎤 Recording started! Speak now...")

    def stop_voice_recording(self):
        """Stop voice recording and process audio."""
        if st.session_state.recording:
            st.session_state.recording = False
            audio_data = st.session_state.audio_recorder.stop_recording()
            
            if audio_data is not None:
                with st.spinner("Converting speech to text..."):
                    transcript = self.stt_service.transcribe_audio_data(audio_data)
                    
                if transcript:
                    # Add user message to conversation
                    st.session_state.current_conversation.append({
                        "role": "user",
                        "content": transcript
                    })
                    
                    # Generate and add assistant response
                    with st.spinner("Generating response..."):
                        response = self.llm_service.generate_response(transcript, st.session_state.current_conversation[:-1])
                    
                    if self.add_assistant_response(response):
                        st.success("✅ Voice message processed successfully!")
                        return True
                else:
                    st.error("❌ Failed to transcribe audio. Please try again.")
            else:
                st.error("❌ No audio recorded. Please try again.")
        
        return False


    def run(self, groq_available, model_config):
        """Main application runner."""
        self.setup_page_config()
        self.add_autoplay_script()
        
        # Render sidebar
        self.render_sidebar(groq_available, model_config)
        
        # Render main interface
        self.render_main_interface(groq_available, model_config)
        
        # Handle immediate TTS (right after main interface)
        self.render_immediate_tts_section()
        
        # Handle voice input
        self.render_voice_input_controls()
        
        # Render footer
        self.render_footer()

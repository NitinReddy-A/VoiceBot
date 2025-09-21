"""
Audio recording functionality for the VoiceBot application.
Handles real-time audio recording using sounddevice.
"""

import threading
import queue
import time
import numpy as np
import sounddevice as sd
from config import SAMPLE_RATE, CHANNELS


class AudioRecorder:
    """Handles real-time audio recording with threading support."""
    
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.audio_thread = None

    def callback(self, indata, frames, time, status):
        """Callback function for audio input stream."""
        if status:
            print(f'Error in audio callback: {status}')
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        """Start audio recording in a separate thread."""
        self.is_recording = True
        self.audio_thread = threading.Thread(target=self._record)
        self.audio_thread.start()

    def _record(self):
        """Internal recording method that runs in a separate thread."""
        with sd.InputStream(callback=self.callback,
                          channels=CHANNELS,
                          samplerate=SAMPLE_RATE):
            while self.is_recording:
                time.sleep(0.1)

    def stop_recording(self):
        """Stop audio recording and return the recorded audio data."""
        self.is_recording = False
        if self.audio_thread:
            self.audio_thread.join()
        
        audio_chunks = []
        while not self.audio_queue.empty():
            audio_chunks.append(self.audio_queue.get())
        
        if audio_chunks:
            return np.concatenate(audio_chunks)
        return None

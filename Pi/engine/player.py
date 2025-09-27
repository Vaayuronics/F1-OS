import numpy as np
import sounddevice as sd
import queue
import os
import resampy
from threading import Thread, Lock, current_thread
import librosa
from scipy.io import wavfile

SAMPLE_RATE = 44100  # Sample rate for audio playback
   
class EngineAudioPlayer:
    def __init__(self, chunk_duration : float = 1.0, channels : int = 2, target : int = 1, max_buffer_size : int = 10):
        '''Smaller chunk size increases reponsiveness'''
        # Increase buffer size and add a minimum buffer threshold
        self.buffer = queue.Queue(maxsize=max_buffer_size)
        self.buffer_target = target
        # Start in running state so writer loop is active
        self.running = True
        self.playback_started = False
        # Volume control (0.0 - 1.0)
        self._volume = 1.0
        self._prev_volume = 1.0
        self.vol_lock = Lock()
        self.queue_lock = Lock()
        self.running_lock = Lock()
        block_size = EngineAudioPlayer._calculate_optimal_blocksize(chunk_duration)

        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=channels,
            dtype='float32',
            blocksize=block_size,
            latency='low'
        )
        self.stream.start()
        
        self.writer_thread = Thread(target=self._buffer_writer, daemon=True)
        self.writer_thread.start()

    def set_volume(self, volume: float) -> None:
        """Set output volume in range [0.0, 1.0]. Values are clamped."""
        try:
            v = float(volume)
        except (TypeError, ValueError):
            return
        if np.isnan(v) or np.isinf(v):
            return
        v = max(0.0, min(1.0, v))
        with self.vol_lock:
            self._volume = v

    def get_volume(self) -> float:
        """Get current output volume (0.0 - 1.0)."""
        with self.vol_lock:
            return self._volume

    @staticmethod
    def _calculate_optimal_blocksize(chunk_duration: float) -> int:
        """Calculate the optimal blocksize based on typical chunk parameters"""
        # Calculate samples for a typical chunk after resampling
        samples_per_chunk = int(chunk_duration * SAMPLE_RATE)
            
        # Make sure it's a power of 2 for optimal performance
        # Find the nearest power of 2 that's equal or greater than our size
        power_of_2 = 2
        while power_of_2 < samples_per_chunk:
            power_of_2 *= 2
            if power_of_2 > 4096:  # Limit to a reasonable maximum
                power_of_2 = 4096
                break
                
        # If we're close to the lower power of 2, use that instead
        if samples_per_chunk < (power_of_2 * 0.75) and power_of_2 > 2:
            power_of_2 //= 2
        
        return power_of_2

    @staticmethod
    def load_audio_wav(path : str) -> tuple[np.ndarray, int]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        audio_data, sample_rate = librosa.load(path, sr=None, mono=False)  # Don't force mono

        if audio_data.dtype != np.float32:
            if np.issubdtype(audio_data.dtype, np.integer):
                audio_data = audio_data / np.iinfo(audio_data.dtype).max
            audio_data = audio_data.astype(np.float32)

        # Determine number of channels
        if audio_data.ndim == 1:
            channels = 1
        else:
            # librosa loads multi-channel as (channels, samples)
            channels = audio_data.shape[0]
            # If we have more samples than channels, transpose to (samples, channels)
            if audio_data.shape[0] > audio_data.shape[1]:
                audio_data = audio_data.T
                channels = audio_data.shape[1]

        if sample_rate != SAMPLE_RATE:
            if audio_data.ndim == 1:
                audio_data = resampy.resample(audio_data, sample_rate, SAMPLE_RATE)
            else:
                # For multi-channel, resample each channel
                resampled = []
                for i in range(channels):
                    resampled.append(resampy.resample(audio_data[:, i], sample_rate, SAMPLE_RATE))
                audio_data = np.column_stack(resampled)
    
        return audio_data, channels

    @staticmethod
    def transform_audio(data : np.ndarray, start_time : float, duration : float,speed : float) -> np.ndarray:
        '''Change audio speed without affecting pitch\n
        Also get the specific timing of the audio data'''
        start_sample = int(start_time * SAMPLE_RATE)
        
        # Get total samples - handle both mono and multi-channel audio
        if data.ndim == 1:
            total_samples = data.shape[0]
        else:
            total_samples = data.shape[1]  # For multi-channel (channels, samples)
            
        requested_samples = int(duration * SAMPLE_RATE)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            # End of file reached
            return None

        # Slice the audio data properly
        if data.ndim == 1:
            sliced_data = data[start_sample:min(end_sample, total_samples)]
        else:
            sliced_data = data[:, start_sample:min(end_sample, total_samples)]

        if speed == 1.0:
            return sliced_data
        
        return librosa.effects.time_stretch(sliced_data, rate=speed)

    @staticmethod
    def save_audio_wav(path : str, data : np.ndarray) -> None:
        wavfile.write(path, SAMPLE_RATE, data)

    @staticmethod
    def get_dur(data : np.ndarray) -> float:
        '''Get audio data duration'''
        if data.ndim == 1:
            return len(data) / SAMPLE_RATE
        else:
            # For multi-channel audio, get the number of samples (largest dimension)
            return data.shape[1] / SAMPLE_RATE

    @staticmethod
    def load_audio(path : str) -> np.ndarray:
        '''Load a npy file containing audio data'''
        return np.load(path)

    @staticmethod
    def save_audio(path : str, data : np.ndarray) -> None:
        '''Save audio data to a npy file'''
        np.save(path, data)

    def _buffer_writer(self):
        while True:
            with self.running_lock:
                if not self.running:
                    break
            
            try:
                with self.queue_lock:
                    # Only start consuming when we have enough data
                    if not self.playback_started and self.buffer.qsize() >= self.buffer_target:
                        self.playback_started = True
                    
                    if self.playback_started:
                        chunk = self.buffer.get_nowait()
                    else:
                        chunk = None
                
                if chunk is not None:
                    self.stream.write(chunk)
                    
            except queue.Empty:
                with self.queue_lock:
                    self.playback_started = False
            except Exception as e:
                print(f"Error in audio playback: {e}")
                self.stop()
                break

    def is_playing(self) -> bool:
        """Check if the audio player is currently playing audio."""
        with self.queue_lock:
            return self.playback_started

    def play_chunk(self, data : np.ndarray) -> bool:
        '''Asynchronously play a chunk of audio data\n
        Returns False if buffer is full or player is stopped. True if successful.'''
        if data is None:
            print("Cannot play None audio chunk")
            return False
            
        with self.running_lock:
            if not self.running:
                print("Audio player is not running")
                return False

        # Make sure data is contiguous when putting in buffer
        chunk = data
        
        # sounddevice expects (samples, channels) format, but our audio is in (channels, samples)
        if chunk.ndim == 2 and chunk.shape[0] < chunk.shape[1]:
            # Transpose from (channels, samples) to (samples, channels)
            chunk = chunk.T

        # Get the volume atomically, if not locked use previous value to prevent stutter
        if(not self.vol_lock.locked()):
            with self.vol_lock:
                vol = self._volume
                self._prev_volume = vol
        else:
            vol = self._prev_volume
        # Apply volume scaling
        if vol != 1.0:
            chunk = (chunk * np.float32(vol)).astype(np.float32, copy=False)

        chunk = np.ascontiguousarray(chunk, dtype=np.float32)
    
        try:
            with self.queue_lock:
                self.buffer.put_nowait(chunk)
        except queue.Full:
            print("Audio buffer full, dropping chunk")
            return False

        return True

    def stop(self):
        # Signal writer thread to stop and clean up audio stream safely
        print("Stopping audio player")
        with self.running_lock:
            if not self.running:
                return
            self.running = False
        
        with self.queue_lock:
            self.playback_started = False
            # Clear the buffer
            try:
                while True:
                    self.buffer.get_nowait()
            except queue.Empty:
                pass
        # Avoid deadlocking by joining from a different thread
        try:
            if self.writer_thread and current_thread() is not self.writer_thread:
                self.writer_thread.join(timeout=1.0)
        except Exception:
            pass
        # Stop/close stream defensively
        try:
            if self.stream:
                self.stream.stop()
        except Exception:
            pass
        try:
            if self.stream:
                self.stream.close()
        except Exception:
            pass

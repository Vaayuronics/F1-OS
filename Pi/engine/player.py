import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import queue
import os
import resampy
from threading import Thread, Lock, current_thread

SAMPLE_RATE = 44100  # Sample rate for audio playback

class EngineAudioStatus:
    '''Class to represent the status of the audio engine.'''
    def __init__(self, end_of_file, dropped, waitTime, position, error=None):
        self.end_of_file = end_of_file
        self.dropped = dropped
        self.waitTime = waitTime
        self.position = position
        self.error = error
        
    def __getitem__(self, key):
        if key == 'done':
            return self.end_of_file
        elif key == 'dropped':
            return self.dropped
        elif key == 'waitTime':
            return self.waitTime
        elif key == 'position':
            return self.position
        elif key == 'error':
            return self.error
        else:
            raise KeyError(f"Invalid key: {key}")
        
class EngineChunk:
    def __init__(self, data, duration):
        self.data = data
        self.duration = duration

    def __getitem__(self, key):
        if key == 'data':
            return self.data
        elif key == 'duration':
            return self.duration
        else:
            raise KeyError(f"Invalid key: {key}")
        
class EngineAudioPlayer:
    def __init__(self, chunk_duration : int, channels : int = 2, target : int = 1, max_buffer_size : int = 10):
        '''Smaller chunk size increases reponsiveness'''
        # Increase buffer size and add a minimum buffer threshold
        self.buffer = queue.Queue(maxsize=max_buffer_size)
        self.buffer_target = target
        # Start in running state so writer loop is active
        self.running = True
        self.playback_started = False
        # Volume control (0.0 - 1.0)
        self._volume = 1.0
        self._lock = Lock()
        block_size = self._calculate_optimal_blocksize(chunk_duration)

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
        with self._lock:
            self._volume = v

    def get_volume(self) -> float:
        """Get current output volume (0.0 - 1.0)."""
        with self._lock:
            return self._volume

    def _calculate_optimal_blocksize(self, chunk_duration : float) -> int:
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
    def load_and_preprocess_audio(path : str) -> np.ndarray:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        sr, data = wav.read(path)
        if data.dtype != np.float32:
            data = data / np.iinfo(data.dtype).max
        data = data.astype(np.float32)

        if sr != SAMPLE_RATE:
            if data.ndim == 1:
                data = resampy.resample(data, sr, SAMPLE_RATE)
            else:
                data = resampy.resample(data.T, sr, SAMPLE_RATE).T
        return data

    def _buffer_writer(self):
        while self.running:
            try:
                # Only start consuming when we have enough data
                if not self.playback_started and self.buffer.qsize() >= self.buffer_target:
                    self.playback_started = True
                
                if self.playback_started:
                    chunk = self.buffer.get(timeout=0.1)
                    # Snapshot the volume atomically
                    with self._lock:
                        vol = self._volume
                    data = chunk['data']
                    # Apply volume scaling at write time for instant effect
                    if vol != 1.0:
                        out = (data * np.float32(vol)).astype(np.float32, copy=False)
                    else:
                        out = data
                    self.stream.write(out)
            except queue.Empty:
                self.playback_started = False
                pass
            except Exception as e:
                self.stop()

    def play_chunk(self, data : np.ndarray, start_time : float, duration : float) -> EngineAudioStatus:
        if(self.running == False):
            return EngineAudioStatus(False, False, 0, 0, "Audio player is not running.")
        start_sample = int(start_time * SAMPLE_RATE)
        total_samples = data.shape[0]
        requested_samples = int(duration * SAMPLE_RATE)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            # End of file reached
            return EngineAudioStatus(True, False, 0, start_time)

        chunk = data[start_sample:min(end_sample, total_samples)]

        '''
        # Resample for speed
        if speed != 1.0:
            #print("\tResampling chunk")
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, SAMPLE_RATE * speed, SAMPLE_RATE, parallel=True)
            else:
                chunk = resampy.resample(chunk.T, SAMPLE_RATE * speed, SAMPLE_RATE, parallel=True).T
            #print("\tChunk resampled, applying fade")

            # Apply very small fade in/out to reduce clicking
            fade_samples = min(int(0.005 * SAMPLE_RATE), len(chunk) // 8)  # 5ms or 1/8 of chunk
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                if chunk.ndim == 1:  # Mono
                    chunk[:fade_samples] *= fade_in
                    chunk[-fade_samples:] *= fade_out
                else:  # Stereo
                    chunk[:fade_samples] *= fade_in.reshape(-1, 1)
                    chunk[-fade_samples:] *= fade_out.reshape(-1, 1)
                #print("\tFade applied")
        '''

        # Make sure data is contiguous when putting in buffer
        chunk = np.ascontiguousarray(chunk)
    
        dropped = False
        try:
            self.buffer.put_nowait(EngineChunk(chunk, duration))
        except queue.Full:
            dropped = True

        return EngineAudioStatus(False, dropped, duration, start_time + duration)

    def stop(self):
        # Signal writer thread to stop and clean up audio stream safely
        self.running = False
        self.playback_started = False
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

import time
from engine.player import EngineAudioPlayer

BASE_INPUT_PATH = "engine/audio/"
BASE_OUTPUT_PATH = "engine/modio/"
CHANNELS = 2


def test_latency():
    '''NOTE: Initial stretch for librosa module as a whole will take a long time. Use librosa to play the startup audio at like 1.01 times speed or something to initialize JIT.'''
    audio_data, channels = EngineAudioPlayer.load_audio_wav("audio/accel.wav")
    print(f"Loaded audio: shape={audio_data.shape}, channels={channels}")
    dur = EngineAudioPlayer.get_dur(audio_data)/5
    print(f"Total duration: {EngineAudioPlayer.get_dur(audio_data):.3f}s, chunk duration: {dur:.3f}s")
    player = EngineAudioPlayer(channels=channels)
    start_time = 0
    overall_start = time.time()
    for i in range(1,6):
        start_time = time.time()
        # Use (i*dur) for start time to get sequential chunks
        audio_chunk = player.transform_audio(audio_data, (i-1)*dur, dur, i*2)
        print(f"Transformed chunk shape: {audio_chunk.shape if audio_chunk is not None else None}")
        if audio_chunk is not None:
            print(player.play_chunk(audio_chunk))
        else:
            print("No audio chunk returned")
        end_time = time.time()
        print(f"Playing chunk {i}/5")
        print(f"Chunk duration: {EngineAudioPlayer.get_dur(audio_chunk):.3f}s, Processing time: {end_time - start_time:.3f}s")
    while player.is_playing():
        time.sleep(0.1)
    print(f"Overall elapsed time: {time.time() - overall_start:.3f}s")
    player.stop()

#TODO Implement sound system using EngineAudioPlayer
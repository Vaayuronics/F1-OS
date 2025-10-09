import time
import numpy as np
import librosa
import resampy

# Pre-compile common librosa functions on import to speed up first use
print("[Audio Init] Compiling JIT functions...")
_dummy = np.random.random(4410).astype(np.float32)  # 0.1s of dummy audio
try:
    # Force compilation of time_stretch and related functions
    _ = librosa.effects.time_stretch(_dummy, rate=1.5)
    _ = librosa.effects.time_stretch(_dummy, rate=0.8)
    # Pre-compile resampling too
    _ = resampy.resample(_dummy, 44100, 48000)
    print("[Audio Init] ✓ Audio system initialized and cached")
except Exception as e:
    print(f"[Audio Init] Warning: Could not pre-compile audio functions: {e}")

from engine.player import EngineAudioPlayer

ENGINE_PATH = "engine/audio/"
MUSIC_PATH = "engine/music/"
NOTIFICATIONS_PATH = "engine/notifications/"
notifier = EngineAudioPlayer()
engineer = EngineAudioPlayer(chunk_duration= 0.3, max_buffer_size=3)
musicer = EngineAudioPlayer(max_buffer_size=5)
music = []
f1_v10 = {}
porche = {}
horn = None
track = 0
curtime = 0.0
curmusictime = 0.0
maxed = False
idled = False
notifications = {}
TRACKS = len(music)
porcheMode = False
loaded = False

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

def load_tracks():
    '''Load all tracks into memory.'''
    global music, f1_v10, porche, notifications, loaded
    # Load f1 data
    print("Loading acceleration sound...")
    f1_v10['accel'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "accel.wav")
    print("Loading deceleration sound...")
    f1_v10['decel'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "decel.wav")
    print("Loading idle sound...")
    f1_v10['idle'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "Idle.wav")
    print("Loading start sound...")
    f1_v10['start'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "Start.wav")
    print("Loading stop sound...")
    f1_v10['stop'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "Stop.wav")
    print("Loading max RPM sound...")
    f1_v10['max_rpm'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "max_rpm.wav")
    # Load porche data
    #porche['accel'] = EngineAudioPlayer.load_audio_wav(ENGINE_PATH + "gt3R.wav")
    #TODO: Add more sounds and splice the porche sound into accel, decel, idle, start, stop, max_rpm
    # Horn
    #TODO: Replace with real horn sound
    # Notifications
    #TODO: Add real notification sounds
    #Music
    #TODO: Load music tracks
    loaded = True

def play_startup_sound():
    '''Play the startup sound to initialize audio system.'''
    global loaded
    if not loaded:
        raise Exception("Audio tracks not loaded yet!")
    #TODO: Need to add futureistic startup sound
    pass

def reset_curtime():
    '''Reset the current engine audio time to 0.'''
    global curtime, maxed, idled
    curtime = 0.0
    maxed = False
    idled = False

def play_f1_start():
    '''Play the F1 engine start sound.'''
    global loaded
    if not loaded:
        raise Exception("Audio tracks not loaded yet!")
    engineer.play_chunk(f1_v10['start'])

def set_porche_mode(enabled: bool):
    '''Enable or disable porche engine mode.'''
    global porcheMode
    porcheMode = enabled

def play_horn():
    '''Play the horn sound.'''
    global loaded
    if not loaded:
        raise Exception("Audio tracks not loaded yet!")
    engineer.play_chunk(horn)

def play_engine(accel: bool, speed: float, engine_vol: int = 100):
    '''Play engine sound based on acceleration and speed.'''
    global loaded
    if not loaded:
        raise Exception("Audio tracks not loaded yet!")
    engineer.set_volume(engine_vol / 100.0) # Scale 0-100 to 0.0-1.0
    if porcheMode:
        pass #TODO: Implement porche audio logic
    else:
        play_f1_audio(accel, speed)

def change_track(new_track: int):
    '''Change the current music track.'''
    global track, curmusictime
    if new_track != track:
        new_track = new_track % TRACKS # Wrap around if out of bounds
        track = new_track
        curmusictime = 0.0 # Reset music time to start of new track

def current_track() -> int:
    '''Return the current music track number.'''
    return track

def play_music(music_vol: int = 100):
    '''Play music track based on track number.'''
    global TRACKS, curmusictime, loaded
    if not loaded:
        raise Exception("Audio tracks not loaded yet!")
    musicer.set_volume(music_vol / 100.0) # Scale 0-100 to 0.0-1.0
    chunk = EngineAudioPlayer.transform_audio(music[track], curmusictime, musicer.get_chunk_duration(), 1.0)
    if chunk is None:
        curmusictime = 0.0
        change_track(track+1) # Move to next track if current is done
        chunk = EngineAudioPlayer.transform_audio(music[track], curmusictime, musicer.get_chunk_duration(), 1.0)
    musicer.play_chunk(chunk)
    curmusictime += musicer.get_chunk_duration()

def play_f1_audio(accel: bool, speed: float):
    '''Play F1 engine sound based on acceleration and speed.'''
    global curtime, maxed, idled, loaded
    if not loaded:
        raise Exception("Audio tracks not loaded yet!")
    #NOTE: May need to set speed to 0 when idling or maxed to prevent weird speedups
    data = None
    if accel and maxed:
        data = f1_v10['max_rpm']
    elif not accel and idled:
        data = f1_v10['idle']
    elif accel and not maxed:
        data = f1_v10['accel']
        idled = False # Reset idled when accelerating
    elif not accel and not idled:
        data = f1_v10['decel']
        maxed = False # Reset maxed when decelerating
    data = EngineAudioPlayer.transform_audio(data, curtime, engineer.get_chunk_duration(), speed)
    if data is None:
        if accel and not maxed:
            maxed = True
            curtime = 0.0
            play_f1_audio(accel, speed) # Recursively call to play max rpm sound
            return
        elif not accel and not idled:
            idled = True
            curtime = 0.0
            play_f1_audio(accel, speed) # Recursively call to play idle sound
            return
        else:
            curtime = 0.0
            play_f1_audio(accel, speed) # Recursively call to loop current track
            return
    curtime += engineer.get_chunk_duration() * speed
    engineer.play_chunk(data)
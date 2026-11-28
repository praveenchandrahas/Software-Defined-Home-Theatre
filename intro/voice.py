"""Generate the voice-over, one WAV per spoken line of the score, with the Kokoro-82M text-to-speech model.

usage: python3 voice.py [voice-name]     model files in ./models (./get-voice-model.sh), output in ./vo
Needs: pip install kokoro-onnx soundfile
"""
import os, sys
import soundfile as sf
from kokoro_onnx import Kokoro
import score as S

name = sys.argv[1] if len(sys.argv) > 1 else "af_heart"
tts = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
os.makedirs("vo", exist_ok=True)
for i, (t0, t1, _, say, _) in enumerate(S.CAPTIONS):
    audio, sr = tts.create(say, voice=name, speed=0.92, lang="en-us")
    sf.write("vo/%02d.wav" % i, audio, sr, subtype="PCM_16")
    print("%02d  %.2f s of %.2f  %s" % (i, len(audio) / sr, t1 - t0, say))

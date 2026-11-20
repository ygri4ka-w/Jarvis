"""Check the installed Russian model without a microphone or external actions."""
from time import monotonic
from vosk import Model
from jarvis_voice.recognition import load_recognizer, model_path
from jarvis_commands.router import COMMANDS

model = Model(str(model_path()))
words = {'джарвис'} | {word for phrase in COMMANDS for word in phrase.split()}
missing = sorted(word for word in words if model.vosk_model_find_word(word) < 0)
assert not missing, f'Missing command words: {missing}'
started = monotonic()
recognizer = load_recognizer(16000)
recognizer.input_timestamp = monotonic()
for _ in range(40):
    recognizer.AcceptWaveform(bytes(1600))
print(f'Russian Vosk vocabulary and silence: PASS ({monotonic() - started:.2f}s)')

# Voice subsystem — approved in conversation

Ukrainian, offline multilingual Whisper base (CPU/int8); sounddevice mono int16 microphone capture.
Voice tab has device selection, refresh/retry, microphone level and a cyan live
waveform derived from PCM samples. In silence the wave is flat. No synthetic
animation, recording or audio upload. Model is downloaded once and stored in
models/faster-whisper-base next to source or packaged executable.

Accept final utterances only: "Джарвіс, <command>" or "Джарвіс" followed by
one command beginning within five seconds after the UI acknowledges the wake.
Carry the utterance start capture timestamp through decoding; decoding time
does not consume the command window. Match whole normalized phrases, not arbitrary
substrings; unknown input cannot execute. No shell text from recognized speech.
Supported commands: open calculator, notepad, default browser, display current
time, stop assistant. Deduplicate identical commands within two seconds.
Return text results, not synthesized speech.

Qt-free command gate and action runner are separate from capture/recognizer.
Microphone callback copies PCM into a bounded queue and updates a compact
waveform mailbox. Whisper runs in QThread. GUI polls waveform at 30 FPS.
During Whisper decoding keep the waveform live, discard new PCM and show a
processing status. Resume capture for commands when decoding finishes. Queued
audio older than five seconds is an error; expected decoding time is separate
from queue age. Recheck stop/errors/device activity after decoding. Queue
overflow or lost input ends the voice session. Failures clear the waveform and offer manual retry.
Stop ignores pending recognitions and asynchronously waits for both workers.
Camera failures do not stop voice and voice failures do not stop camera.

Tests use injected audio/recognizer/action boundaries and actual Qt event loop.
Verify wake gating, expiry, duplicate filtering, exact dispatch, errors,
waveform amplitude, stop during load, and joint close. Separately load the real
model and execute an offline smoke check. Physical speech accuracy requires a user trial.


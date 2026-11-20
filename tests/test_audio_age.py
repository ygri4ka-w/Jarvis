def test_audio_timestamp_preserved_at_capture():
    from jarvis_voice.audio import AudioInbox
    inbox = AudioInbox(clock=lambda: 123.5)
    inbox.callback(bytes(640), 320, None, None)
    timestamp, pcm = inbox.blocks.get_nowait()
    assert timestamp == 123.5
    assert len(pcm) == 640


def test_waveform_continues_but_speech_is_not_queued_during_decode():
    import numpy as np
    from jarvis_voice.audio import AudioInbox
    inbox = AudioInbox()
    inbox.decoding.set()
    inbox.callback(np.full(320, 8000, dtype='<i2').tobytes(), 320, None, None)
    assert max(inbox.take_wave()) > 0
    assert inbox.blocks.empty()
    inbox.decoding.clear()
    inbox.callback(bytes(640), 320, None, None)
    assert inbox.blocks.qsize() == 1

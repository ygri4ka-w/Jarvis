# Camera design — approved in conversation

Keep Variant 1's dark Ukrainian UI and event journal. Camera navigation shows
a proportional live preview, device index (default 0), and manual reconnect.
Starting the assistant starts capture; stopping or closing requests cancellation.
Only a successfully received frame makes the camera active. Voice, microphone,
and gestures remain explicitly unconnected placeholders.

`jarvis_camera/capture.py` owns OpenCV resources independently of Qt.
`jarvis_camera/worker.py` reads in a QThread and accepts an optional frame
processor (BGR uint8 array in/out) for future MediaPipe. A locked latest-frame
mailbox bounds memory; a UI timer consumes it. No frame backlog is accumulated.
`jarvis_ui/camera_panel.py` displays RGB images with aspect ratio preserved.
The window coordinates state, error messages, stop and retry.

Errors opening or reading a device end capture and release it, with one journal
entry and manual retry. Do not guess whether opening failed because of privacy
permissions, another app, or missing hardware. Stop never calls release from
another thread. While the native camera driver is blocked, keep the UI responsive
and prevent a second capture; closing waits asynchronously for worker completion.
Native driver hangs cannot be forcibly recovered safely with a QThread.

Automated tests use fake capture devices and actual Qt event processing, covering
first frame, error paths, stop/restart, bounded mailbox, display and shutdown.
Physical camera validation is reported separately from simulated tests.

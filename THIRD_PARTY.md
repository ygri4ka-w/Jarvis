# Компоненти та моделі

Моделі завантажуються один раз програмою `setup_models.py` і зберігаються
поруч із JARVIS. Розпізнавання мовлення виконується локально.

- [Vosk](https://github.com/alphacep/vosk-api), моделі
  [RU та EN](https://alphacephei.com/vosk/models) — Apache License 2.0.
- [MediaPipe Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
  і [модель](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task) — Apache License 2.0.
- [Qt/PySide6](https://doc.qt.io/qtforpython-6/licenses.html) — LGPLv3/GPLv3
  або комерційна ліцензія; бібліотеки Qt лежать окремими файлами у `_internal`.
- [OpenCV](https://opencv.org/license/) — Apache License 2.0.

Перед поширенням зберігайте ліцензії й повідомлення про авторство залежностей
разом із повним каталогом `JARVIS`.

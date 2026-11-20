# JARVIS Modernization Implementation Plan

**Goal:** Deliver approved RU/EN offline voice, multi-phrase custom commands,
real hand control and a Ukrainian red/black animated interface with Windows build.
**Spec:** ../specs/2026-11-20-modernization-design.md
**Architecture:** independent voice/command/settings, gesture engine/input adapter,
and UI modules. Integration is explicit at window/controller boundaries.
**Tech Stack:** Python, PySide6, OpenCV, Vosk, MediaPipe Tasks, PyInstaller.

## Global constraints
Existing project remains intact until verification and backed-up deployment.
No actual shutdown, clicks, volume changes or custom app launches during tests.
Preserve user EXE commands through schema migration; UI Ukrainian only.
Voice languages ru/en selectable; offline runtime, models packaged externally.

## Review focus
1. Late results after stop/language switch/test mode must not execute actions.
2. Existing config migration must not lose phrases or overwrite corrupt files.
3. Lost hands/ambiguous pinches cannot click; Esc disables input globally.
4. Mirror coordinates must map to screen exactly once, including boundaries.
5. Frozen build must find Vosk/MediaPipe models and resources without network.

## Tasks and stable interfaces

### 1. Voice, settings, actions and persistence
Owner: backend module implementer. Files: jarvis_voice/*, jarvis_commands/*,
jarvis_settings/*, resources/languages/*.json, tests/test_languages.py,
tests/test_settings.py, tests/test_command_migration.py.
- [ ] Tests first for RU/EN same action, wake gating, unsupported language,
  schema-v1 migration, aliases, duplicate phrases per language, corrupt settings.
- [ ] SettingsStore(path=None): get(key,default=None), set(key,value), values dict.
  Keys language='ru', microphone=None, camera=0, wake_required=True,
  animations=True, tracking_enabled=False, gesture_enabled=False, smoothing=.25.
- [ ] language_profiles(): dictionary ru/en with Ukrainian labels and model names.
  CommandGate(commands=None, language='ru', wake_required=True) preserves accept.
- [ ] CommandStore.save(phrase,exe,item_id=None,*,language='ru',phrases=None,
  action_type='exe',target=None); routes(language='ru'); get(id), items, error.
  Items expose id/language/phrases/action_type/target and legacy phrase/exe.
- [ ] VoiceController retains existing constructor, adds set_language(code),
  set_device(device), set_test_mode(enabled), reload_commands(), language,
  activity(str), level(float), test_result(str,str). Activity values:
  idle/listening/processing/executing/error/stopped. Test mode never executes.
- [ ] VoiceWorker adds language='ru'; load_recognizer(rate,path=None,language='ru').
  Model paths: models/vosk-model-small-ru-0.22 and models/vosk-model-small-en-us-0.15.
- [ ] ActionResult supports close=False; action close_application only closes JARVIS.
  Add youtube; existing shutdown behavior preserved. Test with injected actions.
- [ ] Run module tests with existing Python; report compatibility to UI owner.

### 2. Gesture subsystem
Owner: gesture implementer. Files: jarvis_gestures/*, tests/test_gestures.py,
tests/test_gesture_safety.py. No changes to UI/backend files.
- [ ] Test geometry/state engine on fabricated normalized landmarks: left/right
  click, ambiguous pinch, no repeated click, loss/reset, scroll, smoothing.
- [ ] GestureProcessor: constructor(), set_enabled(tracking:bool,control:bool),
  process(bgr)->bgr, snapshot()->dict, close(), set_smoothing(value).
  Snapshot keys gesture(str Ukrainian), tracking(bool), control(bool),
  error(str), landmarks(list), emergency_stopped(bool).
- [ ] MediaPipe task model: models/hand_landmarker.task. Lazy init on capture
  thread, one hand; annotate native frame before existing mirror operation.
- [ ] Windows input isolated behind injectable adapter. Single click on pinch
  edge; thumb-index left, thumb-middle right; two fingers scroll; index cursor;
  thumb up/down volume. All action states exclusive; loss requires neutral.
- [ ] Global Esc via Windows polling or hotkey, including when app has no focus.
  No native actions in unit tests. Processor errors leave camera functional.

### 3. Ukrainian red/black UI and real-state core
Owner: UI implementer. Files: jarvis_ui/*, tests/test_modern_ui.py. Do not edit
backend/gesture implementation; consume interfaces above.
- [ ] Tests core mode/level, navigation, settings persistence, mic-only control,
  test-mode routing, gesture switches and cancellation on close.
- [ ] Preserve JarvisWindow injections used in old tests where practical.
  Build pages home/commands/camera/settings; functional controls, no placeholders.
- [ ] AnimatedCore.set_state(mode,label=''), set_level(value), set_animations(bool).
  QPainter red concentric rings, bounded FPS, stop timers when hidden/reduced.
- [ ] Commands editor supports language, aliases, EXE/URL, dictionary validation;
  manager shows standard/custom, microphone test routes to isolated voice mode.
- [ ] Camera worker processor=GestureProcessor.process; initialize only on worker;
  controls opt-in; snapshot polled in UI. Processor.close after capture ends.
- [ ] Save model/device/activation/animation/gesture preferences in SettingsStore.
  Restore settings but never arm OS gesture control automatically at startup.
- [ ] Render screenshot home/commands/settings/camera at normal and minimum size.

### 4. Dependencies, assets, integration, review and delivery
Owner: root coordinator. Files requirements.txt, setup_models.py, build_exe.bat,
README.md, docs, tests/integration. Coordinate shared API issues sequentially.
- [ ] Verify compatible dependencies before installation; stage environment if
  dependency changes could break existing runtime. Download RU/EN/task models.
- [ ] Confirm wake/command vocabulary with actual models; offline model smoke.
- [ ] Full tests and compile, check UI screenshots, independent final review.
- [ ] Build EXE with data and models; launch smoke offscreen with injected devices
  or no start, verify no network request and clean shutdown.
- [ ] Back up current files, hash-check concurrent changes, deploy verified
  changes/models/build; preserve settings and model migration backups.
- [ ] Explain new modules and how to test speech/hand accuracy manually.

## Execution decisions
Use focused implementers on disjoint module directories, then integrated tests
and independent review. No git repository exists in the user project; use an
isolated staging directory and deployment manifest instead of commits.

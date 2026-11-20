# Custom commands — approved design

Russian phrases mapped to user-selected existing absolute EXE paths; Ukrainian
UI. Add/edit/delete/manual test controls, atomic persistent per-user APPDATA JSON,
immediate router updates. Built-in phrases and wake prefixes cannot be reused.
Background Vosk dictionary check warns for unknown words; explicit override
allows storing for manual launch. Exe launches as a single argument without a
shell, with its parent as working directory. Missing files yield visible errors.

User additionally requested computer on/off. Implement shutdown with a button
and Russian phrase, requiring explicit confirmation in Ukrainian. Cancel is the
default; Windows command has no forced closure. Do not execute actual shutdown
in tests. Power-on requires another device/Wake-on-LAN and remains awaiting
user details; no pretend local power-on action is added.

Validation: persistence and failure recovery, exact routing, edits/deletion,
launch arguments, dictionary warning/cancel, shutdown confirmation branches,
existing voice/camera tests and visual inspection. 70 tests passed before
deployment; no high/medium issues found in independent code review.

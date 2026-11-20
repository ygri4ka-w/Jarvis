"""The sole native input boundary. Importing or constructing it has no effects."""
import ctypes
import os


class WindowsInput:
    def __init__(self):
        self._api = None

    def _user32(self):
        if os.name != 'nt':
            raise RuntimeError('Керування жестами доступне тільки у Windows.')
        if self._api is None:
            self._api = ctypes.WinDLL('user32', use_last_error=True)
            self._api.GetAsyncKeyState.argtypes = [ctypes.c_int]
            self._api.GetAsyncKeyState.restype = ctypes.c_short
            self._api.GetSystemMetrics.argtypes = [ctypes.c_int]
            self._api.GetSystemMetrics.restype = ctypes.c_int
            self._api.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            self._api.SetCursorPos.restype = ctypes.c_int
        return self._api

    def escape_pressed(self):
        # Works independently of Qt focus and continues when capture has stalled.
        return bool(self._user32().GetAsyncKeyState(0x1B) & 0x8001)

    def move(self, x, y):
        api = self._user32()
        width, height = api.GetSystemMetrics(0), api.GetSystemMetrics(1)
        if not api.SetCursorPos(round(max(0., min(1., x))*(width-1)),
                                round(max(0., min(1., y))*(height-1))):
            raise ctypes.WinError(ctypes.get_last_error())

    def _send(self, *, mouse=None, key=None):
        from ctypes import wintypes
        class Mouse(ctypes.Structure):
            _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                        ('data', wintypes.DWORD), ('flags', wintypes.DWORD),
                        ('time', wintypes.DWORD), ('extra', ctypes.c_size_t)]
        class Keyboard(ctypes.Structure):
            _fields_ = [('key', wintypes.WORD), ('scan', wintypes.WORD),
                        ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                        ('extra', ctypes.c_size_t)]
        class Payload(ctypes.Union):
            _fields_ = [('mouse', Mouse), ('keyboard', Keyboard)]
        class Input(ctypes.Structure):
            _fields_ = [('type', wintypes.DWORD), ('payload', Payload)]
        records = []
        if mouse is not None:
            for flags, data in mouse:
                event = Input()
                event.type = 0
                event.payload.mouse = Mouse(0,0,data & 0xffffffff,flags,0,0)
                records.append(event)
        else:
            for flags in (0, 2):
                event = Input()
                event.type = 1
                event.payload.keyboard = Keyboard(key,0,flags,0,0)
                records.append(event)
        events = (Input * len(records))(*records)
        api = self._user32()
        api.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        api.SendInput.restype = wintypes.UINT
        if api.SendInput(len(events), events, ctypes.sizeof(Input)) != len(events):
            # A partial batch may have delivered only the down event. Best-effort
            # release prevents a stuck button/key before the processor disarms.
            if len(records) == 2:
                release = (Input * 1)(records[-1])
                api.SendInput(1, release, ctypes.sizeof(Input))
            raise RuntimeError('Windows не прийняла команду керування.')

    def click(self, button):
        if button not in ('left', 'right'):
            raise ValueError('Невідома кнопка миші.')
        self._send(mouse=[(2,0),(4,0)] if button == 'left' else [(8,0),(16,0)])

    def scroll(self, steps):
        self._send(mouse=[(0x0800, int(steps)*120)])

    def volume(self, direction):
        self._send(key=0xAF if direction > 0 else 0xAE)

"""Local, packaged language profiles. This module never accesses the network."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import sys


@lru_cache(maxsize=1)
def _profiles():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return {code: json.loads((root / 'resources' / 'languages' / f'{code}.json').read_text(encoding='utf-8'))
            for code in ('ru', 'en')}


def language_profiles():
    return deepcopy(_profiles())


def language_profile(code):
    if code not in _profiles():
        raise ValueError(f'Непідтримувана мова: {code}')
    return deepcopy(_profiles()[code])

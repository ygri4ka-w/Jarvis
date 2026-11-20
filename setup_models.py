"""One-time, explicit model installation. The application never downloads models."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile

MODELS = {
    'ru': ('vosk-model-small-ru-0.22',
           'https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip'),
    'en': ('vosk-model-small-en-us-0.15',
           'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'),
    'hands': ('hand_landmarker.task',
              'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'),
}
VOSK_FILES = ('am/final.mdl', 'conf/model.conf', 'graph/HCLr.fst', 'graph/Gr.fst')


def ready(key, root):
    target = Path(root) / MODELS[key][0]
    if key == 'hands':
        return target.is_file() and target.stat().st_size > 1_000_000
    return all((target / name).is_file() and (target / name).stat().st_size
               for name in VOSK_FILES)


def install(key, root, opener=urlopen):
    root = Path(root).resolve()
    if ready(key, root):
        print(f'Already installed: {MODELS[key][0]}', flush=True)
        return
    root.mkdir(parents=True, exist_ok=True)
    name, url = MODELS[key]
    print(f'Downloading {name}...', flush=True)
    # A failed download/extraction never overwrites an existing model.
    with tempfile.TemporaryDirectory(prefix='.download-', dir=root) as temporary:
        staging = Path(temporary)
        download = staging / ('bundle.zip' if key != 'hands' else name)
        with opener(url, timeout=30) as response, download.open('wb') as output:
            shutil.copyfileobj(response, output)
        if key != 'hands':
            with ZipFile(download) as bundle:
                for member in bundle.infolist():
                    if not (staging / member.filename).resolve().is_relative_to(staging):
                        raise ValueError('Invalid path in model archive')
                bundle.extractall(staging)
        if not ready(key, staging):
            raise ValueError(f'Incomplete model: {name}')
        destination = root / name
        backup = None
        if destination.exists():
            backup = root / f'{name}.backup-{datetime.now():%Y%m%d-%H%M%S-%f}'
            destination.rename(backup)
        try:
            (staging / name).rename(destination)
        except OSError:
            if backup is not None:
                backup.rename(destination)
            raise
    print(f'Ready: {destination}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=MODELS)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent / 'models')
    args = parser.parse_args()
    for key in ([args.only] if args.only else MODELS):
        install(key, args.directory)


if __name__ == '__main__':
    main()

"""Install the Russian Vosk model once; recognition itself stays offline."""
from pathlib import Path
import shutil
from urllib.request import urlopen
from zipfile import ZipFile

MODEL_NAME = 'vosk-model-small-ru-0.22'


def install_model():
    root = Path(__file__).resolve().parent / 'models'
    destination = root / MODEL_NAME
    if (destination / 'am' / 'final.mdl').is_file():
        print(f'Model already installed: {destination}')
        return
    root.mkdir(parents=True, exist_ok=True)
    archive = root / f'{MODEL_NAME}.zip'
    with urlopen(f'https://alphacephei.com/vosk/models/{MODEL_NAME}.zip', timeout=60) as response:
        with archive.open('wb') as output:
            shutil.copyfileobj(response, output)
    with ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if not (root / member.filename).resolve().is_relative_to(root.resolve()):
                raise RuntimeError('Invalid path in model archive')
        bundle.extractall(root)
    if not (destination / 'am' / 'final.mdl').is_file():
        raise RuntimeError('Incomplete model archive')
    print(f'Model ready: {destination}')


if __name__ == '__main__':
    install_model()

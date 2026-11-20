"""Build a portable offline Windows folder: dist/JARVIS/JARVIS.exe."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

from setup_models import MODELS, ready


def main():
    root = Path(__file__).resolve().parent
    missing = [key for key in MODELS if not ready(key, root / 'models')]
    if missing:
        raise SystemExit('Missing models: ' + ', '.join(missing) + '\nRun: python setup_models.py')
    # Keep unrelated tools on the host PATH (notably Poppler's ICU) out of the
    # frozen Qt application. PyInstaller resolves needed wheel DLLs itself.
    windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    clean_path = os.pathsep.join(map(str, (Path(sys.executable).parent,
                                            Path(sys.base_prefix),
                                            windows / 'System32', windows)))
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--onedir', '--windowed', '--name', 'JARVIS',
        '--collect-all', 'vosk', '--collect-all', 'sounddevice',
        '--collect-all', '_sounddevice_data', '--collect-all', 'mediapipe',
        '--add-data', 'resources;resources',
        '--exclude-module', 'pytest', '--exclude-module', 'tkinter',
        '--exclude-module', 'PySide6.QtWebEngineCore',
        '--exclude-module', 'PySide6.QtWebEngineWidgets',
        'main.py',
    ], cwd=root, check=True, env={**os.environ, 'PATH': clean_path})
    destination = root / 'dist' / 'JARVIS'
    for name, _ in MODELS.values():
        source = root / 'models' / name
        target = destination / 'models' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
    shutil.copy2(root / 'README.md', destination / 'README.md')
    shutil.copy2(root / 'THIRD_PARTY.md', destination / 'THIRD_PARTY.md')
    print(f'Built: {destination / "JARVIS.exe"}')


if __name__ == '__main__':
    main()

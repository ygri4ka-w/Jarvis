from io import BytesIO
from zipfile import ZipFile

import pytest

from setup_models import install, ready


def archive(files):
    stream = BytesIO()
    with ZipFile(stream, 'w') as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
    return stream.getvalue()


def test_partial_model_does_not_count_as_installed(tmp_path):
    model = tmp_path / 'vosk-model-small-en-us-0.15'
    (model / 'am').mkdir(parents=True)
    (model / 'am/final.mdl').write_bytes(b'model')
    assert not ready('en', tmp_path)


def test_reject_archive_escape_without_touching_existing_files(tmp_path):
    outside = tmp_path / 'keep.txt'
    outside.write_text('keep')
    data = archive({'../keep.txt': b'changed'})
    with pytest.raises(ValueError, match='archive'):
        install('en', tmp_path / 'models', opener=lambda *a, **kw: BytesIO(data))
    assert outside.read_text() == 'keep'


def test_incomplete_download_does_not_replace_old_model(tmp_path):
    model = tmp_path / 'vosk-model-small-en-us-0.15'
    model.mkdir()
    (model / 'keep.txt').write_text('old')
    data = archive({'vosk-model-small-en-us-0.15/am/final.mdl': b'partial'})
    with pytest.raises(ValueError, match='Incomplete'):
        install('en', tmp_path, opener=lambda *a, **kw: BytesIO(data))
    assert (model / 'keep.txt').read_text() == 'old'

from fastapi.testclient import TestClient
from app.main import app
import io
import pytest

client = TestClient(app)

class DummyRaw:
    def __init__(self, nchan=1, n_times=1000, sfreq=100.0):
        self.info = {'nchan': nchan, 'sfreq': sfreq}
        self.n_times = n_times


@pytest.fixture(autouse=True)
def patch_mne(monkeypatch):
    # patch mne.io.read_raw_edf to return a dummy object so we don't need real EDF files
    import mne
    def fake_read_raw_edf(path, preload=True, verbose=False):
        return DummyRaw(nchan=2, n_times=1000, sfreq=250.0)
    monkeypatch.setattr('mne.io.read_raw_edf', fake_read_raw_edf)
    yield


def test_upload_norm_and_data_and_compare():
    # create fake EDF content (not real EDF but mne is patched)
    fake = io.BytesIO(b"0")
    files = {'file': ('norm.edf', fake, 'application/octet-stream')}
    r = client.post('/upload/norm', files=files)
    assert r.status_code == 200

    fake2 = io.BytesIO(b"0")
    files2 = {'file': ('data.edf', fake2, 'application/octet-stream')}
    r = client.post('/upload/data', files=files2)
    assert r.status_code == 200

    r = client.post('/compare')
    assert r.status_code == 200
    j = r.json()
    assert 'norm_file' in j and 'data_file' in j

    r = client.get('/report')
    assert r.status_code == 200
    assert r.headers['content-type'] == 'application/pdf'

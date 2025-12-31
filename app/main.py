from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import tempfile
import shutil
import json
import io

import mne
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = FastAPI()

# serve static frontend
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')

@app.get('/', response_class=HTMLResponse)
async def index():
    f = Path(__file__).parent / 'static' / 'index.html'
    return HTMLResponse(f.read_text())


# store in-memory references on app.state
app.state.norm = None
app.state.data = None
app.state.result = None


async def _save_upload_temp(upload: UploadFile) -> Path:
    tmp = Path(tempfile.mkdtemp()) / upload.filename
    with tmp.open('wb') as out:
        shutil.copyfileobj(upload.file, out)
    return tmp


@app.post('/upload/norm')
async def upload_norm(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.edf'):
        raise HTTPException(status_code=400, detail='Plik musi mieć rozszerzenie .edf')
    tmp = await _save_upload_temp(file)
    try:
        raw = mne.io.read_raw_edf(str(tmp), preload=True, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Nie można odczytać pliku EDF: {e}')
    app.state.norm = {'filename': file.filename, 'raw': raw}
    return {'filename': file.filename}


@app.post('/upload/data')
async def upload_data(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.edf'):
        raise HTTPException(status_code=400, detail='Plik musi mieć rozszerzenie .edf')
    tmp = await _save_upload_temp(file)
    try:
        raw = mne.io.read_raw_edf(str(tmp), preload=True, verbose=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Nie można odczytać pliku EDF: {e}')
    # basic validation example: require at least one channel
    if raw.info.get('nchan', 0) < 1:
        raise HTTPException(status_code=400, detail='EDF bez kanałów')
    app.state.data = {'filename': file.filename, 'raw': raw}
    return {'filename': file.filename}


@app.post('/compare')
async def compare():
    if not app.state.norm or not app.state.data:
        raise HTTPException(status_code=400, detail='Norma lub dane nie są wczytane')
    # placeholder algorithm: compare number of channels and duration
    norm = app.state.norm['raw']
    data = app.state.data['raw']
    res = {
        'norm_file': app.state.norm['filename'],
        'data_file': app.state.data['filename'],
        'norm_channels': norm.info.get('nchan'),
        'data_channels': data.info.get('nchan'),
        'norm_duration_s': round(norm.n_times / norm.info['sfreq'], 2),
        'data_duration_s': round(data.n_times / data.info['sfreq'], 2),
        'score': 0.0,  # placeholder
        'conclusion': 'Porównanie niezaimplementowane - wynik przykładowy'
    }
    app.state.result = res
    return res


@app.get('/report')
async def report():
    if not app.state.result:
        raise HTTPException(status_code=400, detail='Brak wyniku do raportu')
    # create a simple PDF in-memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont('Helvetica', 12)
    c.drawString(50, 800, 'NeuroFlag - Raport porównania')
    y = 760
    for k, v in app.state.result.items():
        c.drawString(50, y, f'{k}: {v}')
        y -= 20
    c.showPage()
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type='application/pdf', headers={'Content-Disposition':'attachment; filename="report.pdf"'})


@app.get('/result')
async def get_result():
    if not app.state.result:
        raise HTTPException(status_code=404, detail='Brak wyniku')
    return JSONResponse(app.state.result)


@app.get('/health')
async def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='info')

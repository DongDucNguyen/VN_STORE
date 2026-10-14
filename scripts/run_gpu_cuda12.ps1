param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [ValidateSet('cpu', 'cuda', 'hybrid')][string]$EnglishDevice = 'hybrid'
)

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv-ml-gpu/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Thiếu .venv-ml-gpu; xem README mục GPU CUDA 12.'
}

$env:VNSTORE_ML_DEVICE = 'cuda'
$env:VNSTORE_ENGLISH_DEVICE = $EnglishDevice
$env:VNSTORE_ASR_ADAPTER = 'app.ml.asr:BilingualWhisper'
$env:VNSTORE_ASR_PRELOAD_ENGLISH = '1'
$env:VNSTORE_IMAGE_ADAPTER = 'app.ml.image:SigLIP2Base'
$env:VNSTORE_OCR = 'rapidocr-latin'
$env:HF_HUB_OFFLINE = '1'
Remove-Item Env:VNSTORE_ML_TRT -ErrorAction SilentlyContinue

& $python -m uvicorn app.main:app --app-dir (Join-Path $repo 'backend') --host 127.0.0.1 --port $Port
exit $LASTEXITCODE

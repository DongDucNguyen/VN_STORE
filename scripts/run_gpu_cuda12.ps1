param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [ValidateSet('cpu', 'cuda', 'hybrid')][string]$EnglishDevice = 'hybrid',
    # Trợ lý tư vấn: tên class trong app.ml.llm (xem reports/model_selection), 'basic' = không model, 'off' = tắt.
    [string]$Assistant = 'Qwen3_4B_Instruct',
    [ValidateSet('cpu', 'cuda')][string]$AssistantDevice = 'cuda',
    # GPU 6 GB không chứa đủ LLM 4B (~4,2–5,2 GB) cùng voice + ảnh (~5,2 GB): khi trợ lý dùng GPU, voice/ảnh/OCR chạy CPU.
    # -ShareGpu giữ voice/ảnh trên GPU (chỉ dùng với model nhỏ hoặc khi đã đo đủ VRAM).
    [switch]$ShareGpu
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
if ($Assistant -eq 'off') {
    $env:VNSTORE_ASSISTANT = 'off'
    Remove-Item Env:VNSTORE_LLM_ADAPTER -ErrorAction SilentlyContinue
    $env:VNSTORE_LLM_PRELOAD = '0'
} elseif ($Assistant -eq 'basic') {
    $env:VNSTORE_ASSISTANT = 'on'
    Remove-Item Env:VNSTORE_LLM_ADAPTER -ErrorAction SilentlyContinue
    $env:VNSTORE_LLM_PRELOAD = '0'
} else {
    $env:VNSTORE_ASSISTANT = 'on'
    $env:VNSTORE_LLM_ADAPTER = "app.ml.llm:$Assistant"
    $env:VNSTORE_LLM_DEVICE = $AssistantDevice
    $env:VNSTORE_LLM_PRELOAD = '1'
    if ($AssistantDevice -eq 'cuda' -and -not $ShareGpu) {
        $env:VNSTORE_ML_DEVICE = 'cpu'
        $env:VNSTORE_ENGLISH_DEVICE = 'cpu'
        Write-Host 'Trợ lý dùng GPU; voice/ảnh chạy CPU (thêm -ShareGpu để giữ trên GPU).'
    }
}
Remove-Item Env:VNSTORE_ML_TRT -ErrorAction SilentlyContinue

& $python -m uvicorn app.main:app --app-dir (Join-Path $repo 'backend') --host 127.0.0.1 --port $Port
exit $LASTEXITCODE

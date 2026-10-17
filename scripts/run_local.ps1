param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [ValidateSet('auto', 'workstation', 'conservative', 'cpu')][string]$Profile = 'auto',
    [ValidateSet('auto', 'basic', 'off', 'Qwen3_4B_Instruct', 'Qwen3_1_7B')][string]$Assistant = 'auto',
    [ValidateRange(1, 64)][int]$Threads = 4,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv-ml/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Thieu .venv-ml; xem docs/local-workstation.md.' }

$gpu = $null
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $lines = & nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits
    if ($LASTEXITCODE -eq 0 -and $lines) {
        # ONNX adapters use device 0, so inspect the same GPU.
        $parts = @($lines)[0].Split(',').Trim()
        if ($parts.Count -eq 3) {
            $gpu = @{ name = $parts[0]; total_mib = [int]$parts[1]; free_mib = [int]$parts[2] }
        }
    }
}
if ($Profile -eq 'auto') {
    # Full concurrent smoke used about 13.7 GiB above the desktop baseline.
    $Profile = if (-not $gpu) { 'cpu' } elseif ($gpu.total_mib -ge 16000 -and $gpu.free_mib -ge 14500) {
        'workstation'
    } elseif ($gpu.free_mib -ge 6000) { 'conservative' } else { 'cpu' }
}
if ($Profile -ne 'cpu' -and -not $gpu) { throw 'Khong tim thay NVIDIA GPU; chon -Profile cpu.' }
if ($Assistant -eq 'auto') { $Assistant = if ($Profile -eq 'cpu') { 'basic' } else { 'Qwen3_4B_Instruct' } }
if ($Profile -eq 'cpu' -and $Assistant -notin @('off', 'basic')) {
    throw 'Profile CPU dung -Assistant basic/off; model CPU can tai va danh gia rieng.'
}

$settings = @{
    VNSTORE_CATALOG = (Join-Path $repo 'database.json')
    VNSTORE_INCLUDE_DRAFTS = '0'
    VNSTORE_SEARCH_CONFIG = '{"ocr_weight":0.35}'
    VNSTORE_TEXT_ADAPTER = $null
    VNSTORE_ML_DEVICE = $(if ($Profile -eq 'workstation') { 'cuda' } else { 'cpu' })
    VNSTORE_ENGLISH_DEVICE = $(if ($Profile -eq 'workstation') { 'hybrid' } else { 'cpu' })
    VNSTORE_ML_THREADS = "$Threads"
    VNSTORE_LLM_THREADS = "$Threads"
    VNSTORE_ASR_ADAPTER = 'app.ml.asr:BilingualWhisper'
    VNSTORE_ASR_PRELOAD_ENGLISH = '1'
    VNSTORE_IMAGE_ADAPTER = 'app.ml.image:SigLIP2Base'
    VNSTORE_IMAGE_INDEX_AUTOBUILD = '1'
    VNSTORE_IMAGE_MULTI_VIEW = '1'
    VNSTORE_OCR = 'rapidocr-latin'
    VNSTORE_ASSISTANT = $(if ($Assistant -eq 'off') { 'off' } else { 'on' })
    VNSTORE_LLM_ADAPTER = $(if ($Assistant -in @('off', 'basic')) { $null } else { "app.ml.llm:$Assistant" })
    VNSTORE_LLM_DEVICE = $(if ($Profile -eq 'cpu') { 'cpu' } else { 'cuda' })
    VNSTORE_LLM_PRELOAD = $(if ($Assistant -in @('off', 'basic')) { '0' } else { '1' })
    VNSTORE_ML_TRT = $null
    # ORT 1.31 / RTX 5070 Ti: cuDNN SDPA auto stalls on long Qwen decode.
    # Flash/XQA remain available; measured long-turn smoke completes with this disabled.
    ORT_ENABLE_CUDNN_FLASH_ATTENTION = '0'
    HF_HUB_OFFLINE = '1'
}
$previous = @{}
try {
    foreach ($key in $settings.Keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }
    if ($Check) {
        @{ profile = $Profile; gpu = $gpu; python = $python; settings = $settings } | ConvertTo-Json -Depth 4
        & $python -c 'import onnxruntime as o; print(o.__version__, o.get_available_providers())'
    } else {
        Write-Host "VNStore: $Profile / assistant=$Assistant / CPU threads=$Threads / http://127.0.0.1:$Port"
        & $python -m uvicorn app.main:app --app-dir (Join-Path $repo 'backend') --host 127.0.0.1 --port $Port
    }
    $code = $LASTEXITCODE
} finally {
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
}
exit $code

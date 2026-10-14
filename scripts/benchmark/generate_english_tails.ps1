param(
    [string]$OutputDir = 'artifacts/voice_smoke/synthetic-en-tail'
)

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not [IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $repo $OutputDir
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sentences = @(
    'Show me a red bag.',
    'Show me the red bags.',
    'I need a blue cup.',
    'I need the blue cups.',
    'It is in the box.',
    'Put it on the box.',
    'Find a silk scarf.',
    'Find two silk scarves.',
    'The lamp is made of wood.',
    'The lamps are made of wood.'
)
$samples = [Collections.Generic.List[object]]::new()
foreach ($speaker in @(@{ name = 'david'; index = 0 }, @{ name = 'zira'; index = 1 })) {
    for ($i = 0; $i -lt $sentences.Count; $i++) {
        $filename = '{0}-{1:00}.wav' -f $speaker.name, ($i + 1)
        $path = Join-Path $OutputDir $filename
        $voice = New-Object -ComObject SAPI.SpVoice
        $voice.Voice = $voice.GetVoices().Item($speaker.index)
        $stream = New-Object -ComObject SAPI.SpFileStream
        try {
            $stream.Open($path, 3, $false)
            $voice.AudioOutputStream = $stream
            [void]$voice.Speak($sentences[$i], 0)
        }
        finally {
            $stream.Close()
        }
        $samples.Add(@{ speaker = $speaker.name; audio_path = $filename;
                        reference_text = $sentences[$i]; sentence_id = $i + 1 })
    }
}
$manifest = @{ source = 'Windows SAPI desktop voices'; purpose = 'synthetic_smoke_only';
               generated_at = (Get-Date).ToString('o'); samples = $samples }
$json = $manifest | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText((Join-Path $OutputDir 'manifest.json'), $json + "`n",
                        [Text.UTF8Encoding]::new($false))
Write-Output "Generated $($samples.Count) English WAV files in $OutputDir"

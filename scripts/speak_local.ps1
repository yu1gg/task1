$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$voice = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $voice.SelectVoice($env:TASK1_TTS_VOICE)
    $voice.SetOutputToWaveFile($env:TASK1_TTS_WAVE)
    $voice.Speak([Console]::In.ReadToEnd())
} finally {
    $voice.Dispose()
}

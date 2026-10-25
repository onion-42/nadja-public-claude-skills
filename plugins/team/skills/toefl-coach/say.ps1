# Speak English text aloud with the built-in Windows voice, without showing it on screen.
# Used by toefl-coach for Listen and Repeat and for interview questions.
# Linux equivalent: espeak-ng -v en-us "text"  (or: spd-say -l en "text")
param(
    [Parameter(Mandatory = $true)][string]$Text,
    [int]$Rate = 0,                      # -10 (slow) .. 10 (fast); 0 = normal test speed
    [string]$Voice = "Microsoft Zira Desktop"
)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try { $synth.SelectVoice($Voice) } catch { Write-Warning "Voice '$Voice' not found, using the default voice." }
$synth.Rate = $Rate
$synth.Speak($Text)
$synth.Dispose()

# Timer for timed writing drills: a small always-on-top window with a countdown and the current
# template step, plus the same step spoken aloud (useful when the sound is on).
# Start it in the background right after showing the task:
#   powershell -NoProfile -File "<skill-dir>/timer.ps1" -Task Discussion
# (<skill-dir> = the folder of this script and SKILL.md)
# Marks mirror the templates in tasks/writing.md. Windows only; on Linux use a phone timer.
param(
    [Parameter(Mandatory = $true)][ValidateSet("Email", "Discussion")][string]$Task,
    [switch]$Silent
)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing, System.Speech

# Seconds from start -> step text (shown and spoken). The last mark is the time limit.
$AllMarks = @{
    Email = @(
        @(0,   "Read the 3 points"),
        @(30,  "Greeting and purpose"),
        @(60,  "Points 1, 2, 3 - two sentences each"),
        @(330, "Polite closing"),
        @(360, "Check: all 3 points there?"),
        @(420, "Stop. Time is up.")
    )
    Discussion = @(
        @(0,   "Read. Pick ONE side"),
        @(60,  "1. View - one sentence"),
        @(120, "2. Reason + example"),
        @(300, "3. React to a classmate"),
        @(420, "4. Conclusion - one sentence"),
        @(480, "Check your verbs"),
        @(600, "Stop. Time is up.")
    )
}
$marks = $AllMarks[$Task]
$limit = $marks[-1][0]
$CLOSE_AFTER_STOP_S = 60

$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
try { $voice.SelectVoice("Microsoft Zira Desktop") } catch { }

$form = New-Object System.Windows.Forms.Form
$form.Text = "TOEFL $Task"
$form.TopMost = $true
$form.FormBorderStyle = "FixedToolWindow"
$form.Size = New-Object System.Drawing.Size(360, 140)
$form.StartPosition = "Manual"
$area = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$form.Location = New-Object System.Drawing.Point(($area.Right - 380), ($area.Bottom - 160))

$time = New-Object System.Windows.Forms.Label
$time.Font = New-Object System.Drawing.Font("Segoe UI", 28, [System.Drawing.FontStyle]::Bold)
$time.Dock = "Top"
$time.Height = 55
$time.TextAlign = "MiddleCenter"
$step = New-Object System.Windows.Forms.Label
$step.Font = New-Object System.Drawing.Font("Segoe UI", 13)
$step.Dock = "Fill"
$step.TextAlign = "MiddleCenter"
$form.Controls.AddRange(@($step, $time))

# A stopwatch keeps the countdown exact; the UI timer only redraws it.
$clock = [Diagnostics.Stopwatch]::StartNew()
$script:next = 0
$ticker = New-Object System.Windows.Forms.Timer
$ticker.Interval = 250
$ticker.Add_Tick({
    $sec = $clock.Elapsed.TotalSeconds
    while ($script:next -lt $marks.Count -and $sec -ge $marks[$script:next][0]) {
        $step.Text = $marks[$script:next][1]
        if (-not $Silent) { $voice.SpeakAsync($marks[$script:next][1]) | Out-Null }
        $script:next++
    }
    $left = [Math]::Max(0, $limit - $sec)
    $time.Text = "{0:00}:{1:00}" -f [Math]::Floor($left / 60), [Math]::Floor($left % 60)
    if ($left -le 0) { $time.ForeColor = "Red" }
    if ($sec -ge $limit + $CLOSE_AFTER_STOP_S) { $form.Close() }
})
$ticker.Start()
[System.Windows.Forms.Application]::Run($form)
$voice.Dispose()

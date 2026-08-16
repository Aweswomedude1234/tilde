# Tilde shell hook for PowerShell (Windows, and PowerShell on macOS).
# Add this line to your profile. Find it by running:  $PROFILE
#     . "C:\full\path\to\tilde\shell\termark.ps1"
# Then open a new terminal.
#
# What it does: gives each terminal window its own id, and quietly records
# the commands you run so that  `tilde save page`  and
# `tilde save command`  (with no text) have something to save.

# A stable id for this specific terminal window.
if (-not $env:TERMARK_SESSION) {
    $env:TERMARK_SESSION = "pwsh-$PID-$([int](Get-Date -UFormat %s))"
}

# How to call termark. Override $env:TERMARK_BIN if it is not on your PATH.
if (-not $env:TERMARK_BIN) { $env:TERMARK_BIN = "termark" }

# Record each command as it is accepted at the prompt.
# PSReadLine lets us see the exact line the user entered.
if (Get-Module -ListAvailable -Name PSReadLine) {
    Set-PSReadLineKeyHandler -Key Enter -ScriptBlock {
        param($key, $arg)
        $line = $null
        $cursor = $null
        [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
        if ($line -and $line.Trim() -and ($line -notmatch '^\s*termark\s+log')) {
            try { & $env:TERMARK_BIN log $line 2>$null | Out-Null } catch { }
        }
        [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
    }
}
else {
    # Fallback: log the last history entry from the prompt function.
    $global:__termarkPrevPrompt = $function:prompt
    function global:prompt {
        $last = Get-History -Count 1 -ErrorAction SilentlyContinue
        if ($last -and $last.CommandLine -and ($last.CommandLine -notmatch '^\s*termark\s+log')) {
            try { & $env:TERMARK_BIN log $last.CommandLine 2>$null | Out-Null } catch { }
        }
        if ($global:__termarkPrevPrompt) { & $global:__termarkPrevPrompt } else { "PS $($executionContext.SessionState.Path.CurrentLocation)> " }
    }
}

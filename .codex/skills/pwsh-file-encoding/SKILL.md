---
name: pwsh-file-encoding
description: Guides for safely writing files with special characters (Chinese, Unicode, markdown backticks, backslashes) from PowerShell on Windows. Use when writing file content through PowerShell that contains backticks, non-ASCII text, markdown code fences, or escape sequences.
---

# PowerShell File Encoding

## Core rule

When writing file content from PowerShell, always use single-quoted
here-strings, not double-quoted. Double-quoted here-strings treat
backtick as the PowerShell escape character, silently destroying
markdown code spans, control chars, and any character following a
backtick.

Safe pattern:

    $content = @'
    ...literal content...
    '@
    [System.IO.File]::WriteAllText("path", $content,
        [System.Text.UTF8Encoding]::new($false))

`new($false)` produces UTF-8 **without BOM**. Always prefer no-BOM
for portable text files (`.md`, `.py`, `.json`).

## Avoid piping to Python

Never pipe here-strings to Python for file writing. The pipe
re-encodes through the console code page, corrupting non-ASCII
characters (Chinese, Japanese, Korean). Write directly via
`[System.IO.File]::WriteAllText` instead.

Never embed Python in PowerShell strings that contain backticks
or curly braces. PowerShell will parse Python syntax (bullets,
pipes, `do`, `for`) as its own.

## Verification

Write a Python script to a temp file first, then execute it:

    @'
    import os
    ...verify code...
    '@ | Set-Content verify.py -Encoding UTF8
    python verify.py

Or use `Get-Content -Encoding UTF8` and visually confirm.

## Corruption examples

Table of what gets destroyed in double-quoted here-strings:

- Inline code: backtick plus next char consumed as escape
- Code fences: triple backticks reduced or removed
- `\r`, `\n`, `\t` interpreted as CR, LF, tab
- Table pipe chars and `\|` altered
- Unicode corrupted when piped through console
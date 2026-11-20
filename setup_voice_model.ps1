$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'setup_voice_model.py')
if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }

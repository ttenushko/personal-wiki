@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src;%PYTHONPATH%"
python -m wikillm.cli.main %*
endlocal

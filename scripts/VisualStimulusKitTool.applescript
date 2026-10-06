-- Visual Stimulus Kit Tool launcher
-- Open in Script Editor, then File > Export > File Format: Application
-- Save to /Applications/Visual Stimulus Kit Tool.app

set projectDir to "/Users/Seth/GIT/videoannotationtool"
set python to "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
set entrypoint to projectDir & "/videoannotation.py"

do shell script python & " " & quoted form of entrypoint & " > /dev/null 2>&1 &"

# Windows EXE build

Use Windows x64 and Python 3.11. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php and obtain Windows x64 FFmpeg + ffprobe from https://www.ffmpeg.org/download.html. Keep the FFmpeg distribution license notices alongside these tools. End users need none of these build tools.

Run PowerShell in this source directory:

```powershell
py -3.11 -m venv .buildenv
.\.buildenv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.buildenv\Scripts\python.exe -m unittest test_lite
.\.buildenv\Scripts\python.exe build_exe.py --iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' --ffmpeg 'E:\tools\ffmpeg\bin'
```

Outputs: release/BMTS-Lite-Setup-0.1.1-Windows-x64.exe (installer) and release/BMTS-Lite-Source-20260912.zip (source archive). Intermediate build/ and .buildenv/ are excluded from the source archive. Node is not needed to run or build the app. Optional JS syntax check: node --check app.js.

The installer bundles Python bytecode, native dependency libraries, FFmpeg, and web assets. App Python sources are packed in the PyInstaller archive rather than copied as loose .py files. Web HTML/CSS/JS remains inspectable, and bytecode packaging is not encryption. Some dependency sources are required for runtime introspection/JIT. Install directory is user-selectable; data/temp stays inside the installation's data directory. Choose a writable drive with room for media. No firewall changes; listening is exclusively 127.0.0.1. Uninstall preserves user-generated data.

Run the actual packaged engine integration test (creates synthetic video/audio and three real exports):

```powershell
Start-Process -Wait -FilePath '.\build\dist\BMTS-Lite\BMTS-Lite.exe' -ArgumentList '--verify','E:\bmts-verification'
Get-Content E:\bmts-verification\verification.json
```

Release installer is not digitally signed. Windows may show publisher/reputation prompts. Signing can be added when a publisher certificate is available.

# BMTS Lite boundaries

Independent minimal app. Do not change original studio-ui-prototype or .agents/skills/bgm-montage. Fast audio-led montage only; no Agent, project manager, storage settings or timeline editor. Default entire audio duration; selectable auto, 16:9, 9:16, 4:3, 3:4, 1:1, 4:5. Local desktop only: bind 127.0.0.1. Keep access-token and same-origin validation.

2026-09-12: user authorized glass UI, export dialog 480/720/1080 default 1080, GitHub cards, installer EXE and source ZIP. Preserve worker.py and engine files. Use build_exe.py / BUILD.md; output release/. Native save completion is confirmed by file stream closing; browser fallback must not claim disk save completion. Build uses PyInstaller onedir plus Inno Setup; no loose application Python source in install. Data remains beside EXE, uninstall preserves it.

Plain HTML/CSS/JS, Python stdlib HTTP; no new frontend dependencies. Preserve upload/generation progress and recoverable errors. Cross-aspect conversion uses existing blur_fill; no content understanding claims. Check unittest test_lite, node --check app.js, and real frozen EXE --verify. Integration verification creates synthetic media and real exports. Build and QA directories must be excluded from source archive.

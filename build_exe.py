"""Build a compiled app directory, Inno Setup EXE, and source-only ZIP."""
import argparse
import importlib.metadata as metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parent
def build(iscc,ffmpeg):
    os.chdir(ROOT)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','BMTS-Lite','--distpath','build/dist','--workpath','build/work','--specpath','build',
        '--paths',str(ROOT/'engine'),
        *[arg for name in ('index.html','app.js','style.css','glass.css') for arg in ('--add-data',f'{ROOT/name};.')],
        *[arg for name in ('ffmpeg.exe','ffprobe.exe') for arg in ('--add-binary',f'{Path(ffmpeg)/name};runtime/ffmpeg')],
        '--collect-all','librosa','--collect-all','numba','--collect-all','llvmlite','--collect-all','scipy',
        '--hidden-import','analyze_bgm','--hidden-import','timeline_planner','--hidden-import','montage','--hidden-import','visual_intelligence',
        '--exclude-module','torch','--exclude-module','matplotlib','--exclude-module','IPython',str(ROOT/'desktop.py')],check=True)
    notices=ROOT/'build/dist/BMTS-Lite/ThirdParty';notices.mkdir(exist_ok=True)
    for dist in metadata.distributions():
        for file in dist.files or []:
            if any(word in Path(file).name.lower() for word in ('license','copying','notice')):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    target=notices/dist.metadata['Name']/Path(file).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name in ('README.md','BUILD.md'):shutil.copy2(ROOT/name,ROOT/'build/dist/BMTS-Lite'/name)
    version=subprocess.run([str(Path(ffmpeg)/'ffmpeg.exe'),'-version'],capture_output=True,text=True,check=True).stdout
    license_text=subprocess.run([str(Path(ffmpeg)/'ffmpeg.exe'),'-L'],capture_output=True,text=True,check=True).stdout
    (notices/'FFmpeg.txt').write_text(version+'\n'+license_text+'\nBuild provider: https://www.gyan.dev/ffmpeg/builds/\nSource: https://ffmpeg.org/download.html\n',encoding='utf-8')
    subprocess.run([str(iscc),str(ROOT/'installer.iss')],check=True)
    files=['AGENTS.md','README.md','BUILD.md','requirements-build.txt','build_exe.py','installer.iss','desktop.py','server.py','worker.py','verify_release.py','test_lite.py','test_export.cjs','smoke_lite.py','index.html','app.js','style.css','glass.css','Start-Lite.cmd']
    output=ROOT/'release/BMTS-Lite-Source-20260912.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in [*(ROOT/n for n in files),*(ROOT/'engine').glob('*.py')]: archive.write(file,Path('bmts-lite')/file.relative_to(ROOT))
    print(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--iscc',required=True);parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args();build(args.iscc,args.ffmpeg)

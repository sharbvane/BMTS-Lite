"""Reuse the existing audio grammar and renderer, without a visual/Agent stage."""
import copy
import json
import math
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'engine'))
RATIOS = {'16:9': (1920,1080), '9:16': (1080,1920), '4:3': (1440,1080),
          '3:4': (1080,1440), '1:1': (1080,1080), '4:5': (1080,1350)}

def probe(file):
    result = subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(file)],
                            capture_output=True, timeout=60, creationflags=0x08000000 if sys.platform=='win32' else 0)
    if result.returncode: raise ValueError('无法读取文件，请换用可正常播放的视频或音频。')
    return json.loads(result.stdout)

def seconds(info):
    value = float(info.get('format',{}).get('duration',0))
    if not math.isfinite(value) or value <= 0: raise ValueError('无法确定素材时长。')
    return value

def display_ratio(stream):
    w,h = stream['width'],stream['height']
    try:
        a,b = map(float,stream.get('sample_aspect_ratio','1:1').split(':'))
        if a>0 and b>0: w *= a/b
    except (ValueError,ZeroDivisionError): pass
    rotation = next((s.get('rotation',0) for s in stream.get('side_data_list',[]) if 'rotation' in s),stream.get('tags',{}).get('rotate',0))
    if abs(float(rotation))%180 == 90: w,h = h,w
    return w/h

def assign(slots, media, duration, seed):
    rng=random.Random(seed); shots=[]; used=[0]*len(media); previous=-1
    for slot in slots:
        start=round(slot['start']*30)/30; end=round(slot['end']*30)/30; length=end-start
        if length<=0: continue
        # Reuse is intentional for full-song output. Long slots can use several short sources.
        while start < end-0.001:
            candidates=[i for i,m in enumerate(media) if m['duration']>=end-start+.08 and i!=previous]
            if not candidates: candidates=[i for i,m in enumerate(media) if m['duration']>=end-start+.08]
            if not candidates: candidates=[i for i in range(len(media)) if i!=previous] or [previous]
            least=min(used[i] for i in candidates); i=rng.choice([i for i in candidates if used[i]==least])
            m=media[i]; length=min(end-start,math.floor((m['duration']-.08)*30)/30)
            if length<=0: raise ValueError('视频片段太短，请换用至少 0.5 秒的视频。')
            source=rng.uniform(0,max(0,m['duration']-length-.04))
            shots.append({'local_path':m['path'],'source_path':m['path'],'source_start':source,
                'source_end':source+length+.03,'speed':1,'output_start':start,'output_end':start+length,
                'timeline_start':start,'timeline_end':start+length,'output_duration':length,'duration':length,
                'transition_in':'hard_cut','transition_out':'hard_cut','crop_plan':{'mode':'fit','retention':1}})
            start+=length; used[i]+=length; previous=i
    return {'shots':shots,'duration_seconds':round(duration*30)/30,'seed':seed}

def run(directory, request, update):
    from analyze_bgm import analyze_bgm
    from timeline_planner import plan_timeline_slots
    from montage import render_timeline
    directory=Path(directory)
    audio_file=directory/request['media'][-1]['file']
    update('检查音频',3)
    audio_info=probe(audio_file)
    if not any(s['codec_type']=='audio' for s in audio_info['streams']): raise ValueError('音乐文件没有音轨。')
    duration=seconds(audio_info)
    if duration<1 or duration>600: raise ValueError('请选择 1 秒至 10 分钟的音乐；不会自动截断。')
    update('分析整首音乐的节奏',8)
    audio=analyze_bgm(audio_file,directory/'audio-cache',directory/'audiomap.json',target_duration=duration)
    slots=plan_timeline_slots(audio,duration)['slots']
    media=[]; ratios=[]
    for i,item in enumerate(request['media'][:-1]):
        update(f'读取视频信息 {i+1}/{len(request["media"])-1}',22+10*i/(len(request['media'])-1))
        file=directory/item['file']; info=probe(file)
        stream=next((s for s in info['streams'] if s['codec_type']=='video'),None)
        if not stream: raise ValueError(f'第 {i+1} 个素材没有视频画面。')
        length=seconds(info)
        if length<.5: raise ValueError(f'第 {i+1} 个视频不足 0.5 秒，请移除它后重试。')
        media.append({'path':str(file),'duration':length,'ratio':display_ratio(stream)}); ratios.append(display_ratio(stream))
    ratio=request['ratio']
    if ratio=='auto':
        votes=[min(RATIOS,key=lambda r:abs(math.log(value/(RATIOS[r][0]/RATIOS[r][1])))) for value in ratios]
        ratio=max(dict.fromkeys(votes),key=votes.count)
    plan=assign(slots,media,duration,directory.name)
    source_ratios={m['path']:m['ratio'] for m in media}
    for shot in plan['shots']:
        if abs(math.log(source_ratios[shot['local_path']]/(RATIOS[ratio][0]/RATIOS[ratio][1])))>.035:
            shot['crop_plan']['mode']='blur_fill'
    (directory/'timeline.json').write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
    batches=[plan['shots'][i:i+12] for i in range(0,len(plan['shots']),12)]
    for i,shots in enumerate(batches):
        update(f'渲染视频 {i+1}/{len(batches)} 批',34+54*i/len(batches))
        batch=copy.deepcopy(shots); origin=batch[0]['output_start']
        for shot in batch:
            for key in ['output_start','output_end','timeline_start','timeline_end']: shot[key]-=origin
        render_timeline({'duration_seconds':batch[-1]['output_end'],'shots':batch},audio_file,directory/f'batch-{i}.mp4',ratio)
    update('合成完整音乐与视频',90)
    (directory/'concat.txt').write_text('\n'.join(f"file 'batch-{i}.mp4'" for i in range(len(batches))),encoding='utf-8')
    command=['ffmpeg','-v','error','-nostdin','-f','concat','-safe','1','-i',str(directory/'concat.txt'),'-i',str(audio_file),
             '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(directory/'result.mp4')]
    result=subprocess.run(command,capture_output=True,timeout=600,creationflags=0x08000000 if sys.platform=='win32' else 0)
    if result.returncode: raise RuntimeError('合成失败，请再试一次。')
    update('检查成片',97)
    info=probe(directory/'result.mp4'); video=next(s for s in info['streams'] if s['codec_type']=='video')
    if (video['width'],video['height'])!=RATIOS[ratio] or abs(seconds(info)-duration)>.15 or not any(s['codec_type']=='audio' for s in info['streams']):
        raise RuntimeError('成片检查未通过，请重试。')
    check=subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(directory/'result.mp4'),'-f','null','-'],capture_output=True,timeout=600,
                         creationflags=0x08000000 if sys.platform=='win32' else 0)
    if check.returncode or check.stderr.strip(): raise RuntimeError('成片解码检查未通过，请重试。')
    for i in range(len(batches)): (directory/f'batch-{i}.mp4').unlink()
    return {'duration':duration,'ratio':ratio,'shots':len(plan['shots'])}

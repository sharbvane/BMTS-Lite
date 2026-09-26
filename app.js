const $=id=>document.getElementById(id);
const query=new URLSearchParams(location.search);let key=query.get('key')||sessionStorage.getItem('bmts-lite-key')||'';
if(key){if(key!==sessionStorage.getItem('bmts-lite-key'))sessionStorage.removeItem('bmts-lite-job');sessionStorage.setItem('bmts-lite-key',key);}
let videos=[],music=null,urls=[],job=null,busy=false,timer=null,started=0,retryAction=null;
const time=n=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
const endpoint=route=>`${route}?key=${encodeURIComponent(key)}`;
async function api(route,body){const r=await fetch(route,{method:body===undefined?'GET':'POST',headers:{'X-BMTS-Key':key,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw new Error(v.error||'连接电脑失败，请重试。');return v;}
function view(name){for(const n of ['import','progress','result'])$(n+'-view').hidden=n!==name;}
function error(e,action){$('error').textContent=e.message||String(e);$('error-box').hidden=false;retryAction=action;$('retry').hidden=!action;}
function working(){busy=true;$('error-box').hidden=true;view('progress');started=Date.now();clearInterval(timer);timer=setInterval(()=>$('elapsed').textContent=`已用时 ${time((Date.now()-started)/1000)}`,1000);}
function idle(){busy=false;clearInterval(timer);}
function progress(text,value){$('phase').textContent=text;$('progress').value=value;$('percent').textContent=`${Math.round(value)}%`;}
function refresh(){for(const u of urls)URL.revokeObjectURL(u);urls=[];$('thumbs').replaceChildren();for(const file of videos.slice(0,4)){const v=document.createElement('video');const u=URL.createObjectURL(file);urls.push(u);v.src=u;v.muted=true;v.playsInline=true;v.preload='metadata';$('thumbs').append(v);}$('video-label').textContent=videos.length?`已选 ${videos.length} 段 · 点击重新选择`:'选择一段或多段素材';$('audio-label').textContent=music?music.name:'成片长度跟随整首音乐';$('generate').disabled=!videos.length||!music;}
$('pick-video').onclick=()=>$('videos').click();$('pick-audio').onclick=()=>$('music').click();
$('videos').onchange=e=>{videos=Array.from(e.target.files);refresh();};$('music').onchange=e=>{music=e.target.files[0]||null;refresh();};
for(const [id,audio] of [['pick-video',false],['pick-audio',true]]){const el=$(id);el.ondragover=e=>{e.preventDefault();el.classList.add('dragover');};el.ondragleave=()=>el.classList.remove('dragover');el.ondrop=e=>{e.preventDefault();el.classList.remove('dragover');if(audio)music=e.dataTransfer.files[0]||null;else videos=Array.from(e.dataTransfer.files);refresh();};}
function upload(id,index,file,onProgress){return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('PUT',`/api/jobs/${id}/${index}`);xhr.setRequestHeader('X-BMTS-Key',key);xhr.timeout=20*60*1000;xhr.upload.onprogress=e=>onProgress(e.loaded);xhr.onerror=()=>reject(new Error('导入中断，请确认 BMTS Lite 正在运行后重试。'));xhr.ontimeout=()=>reject(new Error('导入超时，请重试。'));xhr.onload=()=>{try{const r=JSON.parse(xhr.responseText);if(xhr.status!==200)throw new Error(r.error||'导入失败');resolve();}catch(e){reject(e);}};xhr.send(file);});}
async function follow(){
    for(;;){const state=await api(`/api/jobs/${job}`);progress(state.phase,state.progress);
        if(state.status==='done'){idle();view('result');$('player').src=endpoint(`/api/jobs/${job}/video`);$('result-info').textContent=`${state.ratio} · ${time(state.duration)} · ${state.shots} 个镜头`;return;}
        if(state.status==='error')throw new Error(state.error||'生成失败，请重新导入。');
        if(state.status==='uploading')throw new Error('素材尚未提交，请返回导入重新生成。');
        await new Promise(r=>setTimeout(r,1500));
    }
}
async function start(){const state=await api(`/api/jobs/${job}`);if(state.status==='uploading')await api(`/api/jobs/${job}/start`,{});sessionStorage.setItem('bmts-lite-job',job);await follow();}
async function resume(){working();try{await start();}catch(e){idle();error(e,resume);}}
async function generate(){if(busy)return;working();let imported=false;try{const files=[...videos,music];const created=await api('/api/jobs',{ratio:$('ratio').value,media:files.map(f=>({name:f.name,size:f.size}))});job=created.id;let loaded=0,total=files.reduce((n,f)=>n+f.size,0);for(const [i,file] of files.entries()){await upload(job,i,file,n=>progress(`导入素材 ${i+1}/${files.length}`,100*(loaded+n)/total));loaded+=file.size;}imported=true;progress('导入完成，开始剪辑',0);await start();}catch(e){idle();error(e,imported?resume:generate);}}
$('generate').onclick=generate;
$('remix').onclick=async()=>{if(busy)return;$('player').pause();working();try{const next=await api(`/api/jobs/${job}/remix`,{});job=next.id;await start();}catch(e){idle();error(e,async()=>{working();try{await start();}catch(e){idle();error(e,null);}});}};
$('new').onclick=$('back').onclick=()=>{if(busy)return;$('player').pause();view('import');$('error-box').hidden=true;sessionStorage.removeItem('bmts-lite-job');};
$('retry').onclick=()=>{const fn=retryAction;$('error-box').hidden=true;fn?.();};
$('brand').onclick=e=>{e.preventDefault();if(!busy)$('new').click();};
window.addEventListener('beforeunload',e=>{if(busy){e.preventDefault();e.returnValue='';}});
if(!key)error(new Error('请重新打开 BMTS Lite。'),null);
else if(sessionStorage.getItem('bmts-lite-job')){job=sessionStorage.getItem('bmts-lite-job');working();follow().catch(e=>{idle();error(e,()=>{working();follow().catch(e=>{idle();error(e,null);});});});}

const exportDialog=$('export-dialog');let exporting=false;
async function closeExport(){if(exporting)return;exportDialog.classList.add('closing');await new Promise(r=>setTimeout(r,180));exportDialog.close();exportDialog.classList.remove('closing');}
$('download').onclick=()=>{$('export-options').hidden=false;$('export-success').hidden=true;$('export-status').textContent='';document.querySelector('input[name="resolution"][value="1080"]').checked=true;exportDialog.showModal();};
$('close-export').onclick=$('finish-export').onclick=closeExport;
exportDialog.oncancel=e=>{e.preventDefault();closeExport();};
exportDialog.onclick=e=>{if(e.target===exportDialog){const r=exportDialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeExport();}};
$('confirm-export').onclick=async()=>{
    if(exporting)return;
    const resolution=Number(document.querySelector('input[name="resolution"]:checked').value);
    let handle=null;
    exporting=true;busy=true;$('confirm-export').disabled=true;$('close-export').disabled=true;document.querySelector('.resolutions').disabled=true;
    $('export-status').textContent=window.showSaveFilePicker?'请选择保存位置…':`正在准备 ${resolution}p 视频…`;
    try{
        // Ask while user activation is live; write success is confirmed only after close().
        if(window.showSaveFilePicker)handle=await showSaveFilePicker({suggestedName:`BMTS-Lite-${resolution}p.mp4`,types:[{description:'MP4 视频',accept:{'video/mp4':['.mp4']}}]});
        $('export-status').textContent=`正在准备 ${resolution}p 视频…`;
        await api(`/api/jobs/${job}/export`,{resolution});
        const url=endpoint(`/api/jobs/${job}/export`)+`&resolution=${resolution}`;
        if(handle){
            const response=await fetch(url);if(!response.ok)throw new Error('读取导出文件失败，请重试。');
            const file=await handle.createWritable();
            await response.body.pipeTo(file);
            $('saved-title').textContent='视频已保存';$('saved-detail').textContent=`${resolution}p · ${handle.name}`;
        }else{
            const link=document.createElement('a');link.href=url;link.download=`BMTS-Lite-${resolution}p.mp4`;document.body.append(link);link.click();link.remove();
            $('saved-title').textContent='视频已准备好';$('saved-detail').textContent='已交给浏览器下载，可在下载列表查看保存状态。';
        }
        $('export-options').hidden=true;$('export-status').textContent='';$('export-success').hidden=false;
    }catch(e){$('export-status').textContent=e.name==='AbortError'?'已取消保存。':e.message||'保存失败，请重试。';}
    finally{exporting=false;busy=false;$('confirm-export').disabled=false;$('close-export').disabled=false;document.querySelector('.resolutions').disabled=false;}
};

// Local DOM contract test: no browser or generated-file writes.
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const elements=new Map();
function el(id){if(!elements.has(id))elements.set(id,{hidden:false,disabled:false,textContent:'',classList:{add(){},remove(){}},replaceChildren(){},pause(){},click(){},remove(){},showModal(){this.open=true;},close(){this.open=false;}});return elements.get(id);}
const radio={value:'1080',checked:true},fieldset={disabled:false};
let mode='save',writes=0,downloads=0,resolveWrite;
const fetch=async()=>({ok:true,json:async()=>({resolution:1080}),body:{pipeTo:async()=>{writes++;await new Promise(r=>resolveWrite=r);}}});
const picker=async()=>{if(mode==='cancel')throw Object.assign(new Error('cancel'),{name:'AbortError'});return {name:'test.mp4',createWritable:async()=>({})};};
const context={URL,URLSearchParams,Date,Math,String,Number,Array,Promise,Error,setTimeout,setInterval,clearInterval,fetch,showSaveFilePicker:picker,location:{search:'?key=test'},sessionStorage:{getItem(){return null},setItem(){},removeItem(){}},document:{getElementById:el,querySelector:s=>s==='.resolutions'?fieldset:radio,createElement:()=>({click(){downloads++},remove(){}}),body:{append(){}}},window:{addEventListener(){},showSaveFilePicker:picker}};
vm.createContext(context);vm.runInContext(readFileSync(__dirname+'/app.js','utf8'),context);
(async()=>{
    el('download').onclick();assert.equal(radio.checked,true);assert.equal(el('export-success').hidden,true);
    const saving=el('confirm-export').onclick();
    await new Promise(setImmediate);
    assert.equal(writes,1);assert.equal(el('export-success').hidden,true);assert.equal(fieldset.disabled,true);
    resolveWrite();await saving;assert.equal(el('saved-title').textContent,'视频已保存');assert.equal(el('export-success').hidden,false);
    mode='cancel';el('download').onclick();await el('confirm-export').onclick();assert.equal(el('export-status').textContent,'已取消保存。');assert.equal(el('confirm-export').disabled,false);
    context.window.showSaveFilePicker=undefined;el('download').onclick();await el('confirm-export').onclick();assert.equal(downloads,1);assert.equal(el('saved-title').textContent,'视频已准备好');
    console.log('PASS: native save completion, cancel recovery, download fallback, default 1080p');
})().catch(e=>{console.error(e);process.exitCode=1;});

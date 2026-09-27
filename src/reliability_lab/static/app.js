const $ = id => document.getElementById(id);
let active = null, timer = null;
const pretty = value => String(value).replaceAll('_',' ');
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n; };
async function request(path, options){const r=await fetch(path,options);const body=await r.json();if(!r.ok)throw Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail));return body;}
async function history(){const runs=await request('/api/runs');$('count').textContent=runs.length;$('history').replaceChildren();for(const r of runs){const b=el('button',undefined,'history-item'+(r.id===active?' active':''));b.append(el('strong',pretty(r.request.scenario)),el('small',r.request.mode+' / '+pretty(r.outcome||r.status)));b.onclick=()=>select(r.id);$('history').append(b);}}
function show(data){
 const result=data.result;const events=data.events.filter(e=>e.role!=='model_usage');
 $('headline').textContent=pretty(result?.decision.cause||data.request.scenario);
 $('badge').textContent=pretty(result?.outcome||data.status).toUpperCase();
 $('summary').replaceChildren(el('p',result?.decision.explanation||data.error||'Investigation in progress. Stages and evidence appear as they complete.'));
 if(result){$('summary').append(el('small',result.model+' · '+result.topology+' · snapshot '+result.snapshot_hash.slice(0,12)));}
 $('trace').replaceChildren();const max=Math.max(1,...events.map(e=>e.duration_ms));
 for(const e of events){const row=el('div',undefined,'stage');const bar=el('div',undefined,'bar');const fill=el('i');fill.style.width=(e.duration_ms/max*100)+'%';bar.append(fill);row.append(el('span',e.status==='ok'?'✓':'!','dot'),el('span',pretty(e.role)),bar,el('small',(e.duration_ms/1000).toFixed(2)+' s'));row.title='Trace '+e.trace_id;$('trace').append(row);}
 if(!events.length)$('trace').append(el('p','Waiting for the worker…','muted'));
 $('evidence').replaceChildren();for(const [key,value]of Object.entries(result?.evidence||{})){const d=el('details');d.append(el('summary',key),el('pre',typeof value==='string'?value:JSON.stringify(value,null,2)));$('evidence').append(d);}
 $('repair').replaceChildren(el('p',result?.candidate_sql?'Candidate SQL — exported for review; source untouched.':'No repair proposed.','muted'));if(result?.candidate_sql)$('repair').append(el('pre',result.candidate_sql));if(result?.diff){const d=el('details');d.append(el('summary','Inspect unified diff'),el('pre',result.diff));$('repair').append(d);}
 $('checks').replaceChildren();for(const check of result?.verification?.checks||[]){const row=el('div',undefined,'check');row.append(el('span',pretty(check.name)),el('span',check.passed?'PASS':'FAIL',check.passed?'pass':'fail'));$('checks').append(row);}if(!result?.verification)$('checks').append(el('p','No candidate verification for abstained or pending investigations.','muted'));
 if(result?.verification)$('checks').append(el('p',result.verification.method,'muted'));
 $('downloads').replaceChildren();if(result)for(const name of ['report.json','report.md','candidate.sql','repair.diff']){const a=el('a','↓ '+name);a.href='/api/runs/'+data.id+'/artifacts/'+name;$('downloads').append(a);}
 if(data.status==='failed'){const b=el('button','Resume from checkpoint');b.onclick=async()=>{try{await request('/api/runs/'+data.id+'/resume',{method:'POST'});select(data.id);}catch(e){$('notice').textContent=e.message;}};$('downloads').append(b);}
 return ['completed','failed'].includes(data.status);
}
async function select(id){active=id;clearTimeout(timer);await history();try{const done=show(await request('/api/runs/'+id));if(!done)timer=setTimeout(()=>select(id),800);}catch(e){$('notice').textContent=e.message;}}
$('run').onclick=async()=>{const b=$('run');b.disabled=true;try{const r=await request('/api/runs',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({scenario:$('scenario').value,mode:$('mode').value,topology:$('topology').value,seed:11})});await select(r.run_id);}catch(e){$('notice').textContent=e.message;}finally{b.disabled=false;}};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(t=>t.setAttribute('aria-selected',String(t===b)));document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==b.dataset.tab);});
$('mode').onchange=()=>{$('notice').textContent=$('mode').value==='demo'?'Demo uses deterministic policies, not LLM reasoning.':'Live uses your server-configured model endpoint. API credentials stay on the server.';};
history().catch(e=>$('notice').textContent=e.message);


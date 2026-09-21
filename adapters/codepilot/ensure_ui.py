from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "Documents" / "AgentHub" / "adapters" / "codepilot"
LOG = ROOT / "ui-patch.log"
STATE = ROOT / "ui-state.json"
INSTALL = HOME / "AppData" / "Local" / "Programs" / "CodePilot" / "resources" / "standalone"
STATIC = INSTALL / ".next" / "static" / "chunks"
LEGACY_MARK = "/*__AGENTHUB_CODEPILOT_UI_V01__*/"
MARK = "/*__AGENTHUB_CODEPILOT_UI_V02__*/"
VERSION = "0.2.0"

CLIENT_IIFE = r'''
;/*__AGENTHUB_CODEPILOT_UI_V02__*/
(()=>{try{
if(typeof window==='undefined'||window.__AGENTHUB_CODEPILOT_UI_V02__)return;
window.__AGENTHUB_CODEPILOT_UI_V02__=true;
const HUB='http://127.0.0.1:8765';
let stream=null,currentRun='',followLatest=true,panelOpen=false,refreshTimer=null,scheduled=false;

function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const statusZh={idle:'空闲',created:'已创建',routing:'选择模型',ready:'准备执行',running:'执行中',waiting:'等待',blocked:'阻塞',completed:'已完成',failed:'失败',timed_out:'超时',unknown:'未知'};
const eventZh={'run.created':'任务创建','run.completed':'任务完成','run.failed':'任务失败','agent.created':'Agent 创建','agent.routing':'正在选择模型','agent.routed':'模型已分配','agent.started':'开始执行','agent.message':'新消息','agent.waiting':'等待依赖','agent.blocked':'任务阻塞','agent.completed':'执行完成','agent.failed':'执行失败'};
function fmtTime(v){if(!v)return'';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}
function fmtUpdated(v){if(!v)return'等待数据';const d=typeof v==='number'?new Date(v*1000):new Date(v);return Number.isNaN(d.getTime())?'已同步':'最后同步 '+d.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}
function metric(v,fallback=0){const n=Number(v);return Number.isFinite(n)?n:fallback}

function makePanel(){
 let host=document.getElementById('codepilot-agenthub-panel-host');
 if(host)return host;
 host=document.createElement('div');host.id='codepilot-agenthub-panel-host';
 host.style.cssText='position:fixed;inset:18px;z-index:2147483000;display:none;';
 const root=host.attachShadow({mode:'open'});
 root.innerHTML=`
 <style>
 :host{all:initial}
 *{box-sizing:border-box}
 .shell{height:100%;display:flex;flex-direction:column;overflow:hidden;background:var(--background,#0d1117);color:var(--foreground,#eef2f7);border:1px solid var(--border,#2b3442);border-radius:14px;box-shadow:0 18px 60px rgba(0,0,0,.38);font:14px/1.5 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}
 .head{display:flex;gap:14px;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--border,#2b3442);background:var(--card,var(--background,#0d1117))}
 .brand{min-width:0}.title{font-size:18px;font-weight:700}.subtitle{font-size:12px;color:var(--muted-foreground,#8f9aaa);margin-top:2px}
 .actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
 button,select{font:inherit;color:inherit;background:var(--secondary,#171d27);border:1px solid var(--border,#2b3442);border-radius:8px;padding:7px 10px;min-height:34px}
 button{cursor:pointer}.close{font-size:18px;line-height:18px;padding:7px 11px}
 .follow{display:flex;align-items:center;gap:6px;color:var(--muted-foreground,#8f9aaa);white-space:nowrap}.follow input{width:16px;height:16px}
 .conn{display:flex;align-items:center;gap:6px;color:var(--muted-foreground,#8f9aaa);white-space:nowrap}.dot{width:8px;height:8px;border-radius:50%;background:#8f9aaa}.dot.live{background:#48c983}.dot.err{background:#f06d6d}
 .body{flex:1;overflow:auto;padding:16px;background:var(--background,#0d1117)}
 .summary{display:grid;grid-template-columns:minmax(0,2fr) repeat(5,minmax(92px,.58fr));gap:10px;margin-bottom:16px}
 .card{background:var(--card,#141a23);border:1px solid var(--border,#2b3442);border-radius:11px;padding:12px;min-width:0}
 .card.issue .big{color:#f06d6d}.card.ok .big{color:#48c983}.card.live .big{color:#64a7ff}
 .k{font-size:12px;color:var(--muted-foreground,#8f9aaa)}.v{margin-top:4px;font-weight:650;overflow-wrap:anywhere}.big{font-size:18px}.sub{margin-top:4px;font-size:12px;color:var(--muted-foreground,#8f9aaa);overflow-wrap:anywhere}
 .sec{display:flex;align-items:center;justify-content:space-between;margin:17px 0 9px}.sec h3{font-size:15px;margin:0}.sec span{font-size:12px;color:var(--muted-foreground,#8f9aaa)}
 .agents{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:10px}
 .agent{background:var(--card,#141a23);border:1px solid var(--border,#2b3442);border-radius:11px;padding:12px;min-width:0}
 .atop{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.aname{font-weight:700;font-size:15px;overflow-wrap:anywhere}
 .badge{border:1px solid var(--border,#2b3442);border-radius:999px;padding:2px 7px;font-size:12px;white-space:nowrap}
 .completed{color:#48c983}.running,.routing,.ready{color:#64a7ff}.failed,.blocked{color:#f06d6d}.waiting,.created,.unknown{color:#efb458}
 .rows{display:grid;gap:6px;margin-top:10px}.row{display:grid;grid-template-columns:58px minmax(0,1fr);gap:8px}.row .rv{overflow-wrap:anywhere}
 .block{border-top:1px solid var(--border,#2b3442);padding-top:9px;margin-top:9px}.block .bv{margin-top:3px;white-space:pre-wrap;overflow-wrap:anywhere}
 .events{background:var(--card,#141a23);border:1px solid var(--border,#2b3442);border-radius:11px;overflow:hidden}
 .event{display:grid;grid-template-columns:84px 128px 110px minmax(0,1fr);gap:9px;padding:8px 10px;border-top:1px solid var(--border,#2b3442);align-items:start}.event:first-child{border-top:0}.time,.source{font-size:12px;color:var(--muted-foreground,#8f9aaa)}.etype{font:12px Consolas,monospace}.desc{overflow-wrap:anywhere}
 .empty{padding:28px;text-align:center;color:var(--muted-foreground,#8f9aaa);background:var(--card,#141a23);border:1px dashed var(--border,#2b3442);border-radius:11px}
 .offline{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:280px;gap:10px;text-align:center}.offline strong{font-size:17px}.offline p{margin:0;color:var(--muted-foreground,#8f9aaa)}
 @media(max-width:780px){.shell{border-radius:8px}.head{align-items:flex-start;flex-direction:column}.actions{justify-content:flex-start}.summary{grid-template-columns:1fr 1fr}.summary .title-card{grid-column:1/-1}.event{grid-template-columns:72px minmax(0,1fr)}.source,.desc{grid-column:2}.source{display:none}}
 </style>
 <div class="shell">
   <div class="head">
     <div class="brand"><div class="title">AI 团队</div><div class="subtitle">AgentHub · 实时多 Agent 控制台</div></div>
     <div class="actions">
       <select id="runs" aria-label="选择任务"></select>
       <label class="follow"><input id="follow" type="checkbox" checked>跟随最新</label>
       <button id="refresh" type="button">刷新</button>
       <span class="conn"><span id="dot" class="dot"></span><span id="conn">连接中</span></span>
       <button id="close" class="close" type="button" title="关闭">×</button>
     </div>
   </div>
   <div class="body">
     <div id="summary" class="summary"></div>
     <div class="sec"><h3>AI 团队</h3><span id="count">0 个 Agent</span></div>
     <div id="agents" class="agents"></div>
     <div class="sec"><h3>最近事件</h3><span id="updated">等待数据</span></div>
     <div id="events" class="events"></div>
   </div>
 </div>`;
 document.body.appendChild(host);
 const q=id=>root.getElementById(id);
 const ui={root,host,runs:q('runs'),follow:q('follow'),refresh:q('refresh'),close:q('close'),dot:q('dot'),conn:q('conn'),summary:q('summary'),agents:q('agents'),count:q('count'),events:q('events'),updated:q('updated')};
 host.__agenthubUi=ui;
 ui.close.addEventListener('click',closePanel);
 ui.refresh.addEventListener('click',()=>loadRuns(true));
 ui.runs.addEventListener('change',()=>{followLatest=false;ui.follow.checked=false;connect(ui.runs.value)});
 ui.follow.addEventListener('change',()=>{followLatest=ui.follow.checked;if(followLatest)loadRuns(false)});
 return host;
}
function ui(){return makePanel().__agenthubUi}
function conn(ok,text){const u=ui();u.dot.className='dot '+(ok?'live':'err');u.conn.textContent=text}
function summaryCard(k,v,sub='',cls=''){return `<div class="card ${cls}"><div class="k">${esc(k)}</div><div class="v big">${esc(v)}</div>${sub?`<div class="sub">${esc(sub)}</div>`:''}</div>`}
function render(data){
 const u=ui(),agents=Array.isArray(data.agents)?data.agents:[],m=data.metrics&&typeof data.metrics==='object'?data.metrics:{};
 const working=metric(m.working_count,agents.filter(a=>['routing','ready','running'].includes(a.status)).length);
 const waiting=metric(m.waiting_count,agents.filter(a=>a.status==='waiting').length);
 const completed=metric(m.completed_count,agents.filter(a=>a.status==='completed').length);
 const issues=metric(m.issue_count,agents.filter(a=>['failed','blocked','timed_out','stuck','error'].includes(a.status)).length);
 const active=metric(m.active_count,agents.filter(a=>['created','routing','ready','running','waiting'].includes(a.status)).length);
 u.summary.innerHTML=summaryCard('当前任务',data.title||data.run_id||'暂无任务',data.workspace||'','title-card')+summaryCard('任务状态',statusZh[data.status]||data.status||'未知','',issues?'issue':'')+summaryCard('工作中',working,'','live')+summaryCard('等待',waiting)+summaryCard('问题',issues,'',issues?'issue':'ok')+summaryCard('已完成',completed,'','ok');
 u.count.textContent=agents.length+' 个 Agent · '+active+' 活跃';
 u.agents.innerHTML=agents.length?agents.map(a=>{
   const dep=Array.isArray(a.depends_on)&&a.depends_on.length?a.depends_on.join(', '):'—';
   const elapsed=a.elapsed_sec==null?'—':Number(a.elapsed_sec).toFixed(1)+' 秒';
   const since=a.status_since?fmtTime(a.status_since):'—';
   return `<article class="agent"><div class="atop"><div class="aname">${esc(a.name||a.agent_id)}</div><span class="badge ${esc(a.status||'unknown')}">${esc(statusZh[a.status]||a.status||'未知')}</span></div>
   <div class="rows"><div class="row"><div class="k">模型</div><div class="rv">${esc(a.model||a.requested_model||'—')}</div></div><div class="row"><div class="k">角色</div><div class="rv">${esc(a.role||'—')}</div></div><div class="row"><div class="k">状态自</div><div class="rv">${esc(since)}</div></div><div class="row"><div class="k">依赖</div><div class="rv">${esc(dep)}</div></div><div class="row"><div class="k">耗时</div><div class="rv">${esc(elapsed)}</div></div></div>
   ${a.task?`<div class="block"><div class="k">当前任务</div><div class="bv">${esc(a.task)}</div></div>`:''}
   ${a.message?`<div class="block"><div class="k">最新结果 / 消息</div><div class="bv">${esc(a.message)}</div></div>`:''}
   ${a.error?`<div class="block"><div class="k">失败原因</div><div class="bv failed">${esc(a.error)}</div></div>`:''}</article>`}).join(''):'<div class="empty">当前没有 Agent 数据</div>';
 const events=Array.isArray(data.events)?data.events.slice().reverse():[];
 u.events.innerHTML=events.length?events.slice(0,80).map(e=>{const d=e.data&&typeof e.data==='object'?e.data:{};const desc=d.message||d.task||d.error||d.name||'';return `<div class="event"><div class="time">${esc(fmtTime(e.ts))}</div><div class="etype">${esc(eventZh[e.type]||e.type||'event')}</div><div class="source">${esc(d.name||e.agent_id||'run')}</div><div class="desc">${esc(desc)}</div></div>`}).join(''):'<div class="empty" style="border:0">旧任务暂无标准实时事件</div>';
 u.updated.textContent=fmtUpdated(data.updated_at);
}
function offline(err){
 const u=ui();u.summary.innerHTML='';u.count.textContent='0 个 Agent';u.agents.innerHTML=`<div class="offline"><strong>AgentHub 后台正在连接</strong><p>${esc(err||'暂时无法连接本地服务')}</p><button id="retryHub" type="button">重新连接</button></div>`;u.events.innerHTML='<div class="empty" style="border:0">连接成功后这里会实时显示 Agent 事件</div>';u.updated.textContent='等待连接';conn(false,'后台未连接');
 const b=u.root.getElementById('retryHub');if(b)b.addEventListener('click',()=>loadRuns(false));
}
async function loadRuns(keep=true){
 if(!panelOpen)return;
 try{
   const r=await fetch(HUB+'/api/runs',{cache:'no-store',mode:'cors'});if(!r.ok)throw new Error('HTTP '+r.status);
   const payload=await r.json(),runs=Array.isArray(payload.runs)?payload.runs:[],u=ui();
   const before=keep&&!followLatest?(currentRun||u.runs.value):'';
   u.runs.innerHTML=runs.length?runs.map(x=>`<option value="${esc(x.run_id)}">${esc(x.title||x.run_id)} · ${esc(statusZh[x.status]||x.status)} · ${x.agent_count} Agent${metric(x.issue_count)?' · 问题 '+metric(x.issue_count):''}</option>`).join(''):'<option value="">暂无任务</option>';
   const chosen=followLatest?(runs[0]?.run_id||''):(before&&runs.some(x=>x.run_id===before)?before:(runs[0]?.run_id||''));
   u.runs.value=chosen;if(chosen!==currentRun)connect(chosen);if(!chosen){render({title:'暂无团队任务',status:'idle',agents:[],events:[],updated_at:Date.now()/1000});conn(true,'实时同步')}
 }catch(e){offline(e&&e.message?e.message:String(e))}
}
function connect(runId){
 currentRun=runId||'';if(stream){stream.close();stream=null}if(!panelOpen||!currentRun){if(panelOpen)conn(false,'无任务');return}
 conn(false,'连接中');
 try{
   stream=new EventSource(HUB+'/api/stream?run_id='+encodeURIComponent(currentRun));
   stream.addEventListener('snapshot',ev=>{try{render(JSON.parse(ev.data));conn(true,'实时同步')}catch{conn(false,'数据解析失败')}});
   stream.onerror=()=>conn(false,'正在重连');
 }catch(e){offline(e&&e.message?e.message:String(e))}
}
function openPanel(){
 const h=makePanel();panelOpen=true;h.style.display='block';followLatest=true;ui().follow.checked=true;loadRuns(false);
 clearInterval(refreshTimer);refreshTimer=setInterval(()=>loadRuns(true),10000);
}
function closePanel(){
 panelOpen=false;const h=document.getElementById('codepilot-agenthub-panel-host');if(h)h.style.display='none';if(stream){stream.close();stream=null}clearInterval(refreshTimer);refreshTimer=null;
}
function styleBtn(b){b.style.cssText='border:1px solid var(--border);background:var(--muted);color:var(--foreground);padding:3px 8px;border-radius:7px;font-size:11px;line-height:18px;cursor:pointer;white-space:nowrap;flex-shrink:0;'}
function mount(){
 scheduled=false;const submit=document.querySelector('button[data-message-input-submit]');if(!submit)return;const footer=submit.parentElement;if(!footer)return;
 let b=document.getElementById('codepilot-agenthub-button');if(!b||b.parentElement!==footer){if(b)b.remove();b=document.createElement('button');b.type='button';b.id='codepilot-agenthub-button';b.textContent='AI团队';b.title='打开 AgentHub 实时 AI 团队控制台';styleBtn(b);b.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();openPanel()});
 const mode=document.getElementById('codepilot-interaction-mode');if(mode&&mode.parentElement===footer)footer.insertBefore(b,mode);else footer.insertBefore(b,submit)}
}
function queue(){if(scheduled)return;scheduled=true;requestAnimationFrame(mount)}
new MutationObserver(queue).observe(document.documentElement,{childList:true,subtree:true});window.addEventListener('resize',queue);window.addEventListener('popstate',queue);
window.__agentHubCodePilot={version:'0.2.0',open:openPanel,close:closePanel,reload:()=>loadRuns(false)};queue();
}catch(e){console.warn('[AgentHub] CodePilot UI init failed',e)}})();
'''

def log(msg: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def strip_injected_ui(text: str) -> str:
    """Remove a previously appended AgentHub UI patch, keeping CodePilot's original bundle."""
    positions=[]
    for marker in (MARK, LEGACY_MARK):
        for token in (";" + marker, marker):
            pos=text.find(token)
            if pos >= 0:
                positions.append(pos)
    if not positions:
        return text
    return text[:min(positions)].rstrip() + "\n"

def targets():
    out=[]
    if not STATIC.is_dir(): return out
    for p in STATIC.rglob("*.js"):
        try:s=p.read_text(encoding="utf-8",errors="ignore")
        except OSError:continue
        if MARK in s or LEGACY_MARK in s:
            out.append(p);continue
        if "data-message-input-submit" in s and "messageInput.placeholderDefault" in s:
            out.append(p)
    return out

def ensure_patch(quiet=False):
    if not INSTALL.is_dir():
        if not quiet: print(json.dumps({"ok":False,"error":"CodePilot install not found"},ensure_ascii=False))
        return 2
    files=targets()
    if not files:
        if not quiet: print(json.dumps({"ok":False,"error":"frontend target not found"},ensure_ascii=False))
        return 3
    changed=[]
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir=ROOT/"backups"/stamp
    for p in files:
        s=p.read_text(encoding="utf-8",errors="ignore")
        if MARK in s: continue
        rel=p.relative_to(INSTALL);dest=bdir/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        clean=strip_injected_ui(s) if LEGACY_MARK in s else s
        p.write_text(clean.rstrip()+"\n"+CLIENT_IIFE+"\n",encoding="utf-8",newline="")
        changed.append(p)
    errors=[]
    for p in files:
        try:
            cp=subprocess.run(["node","--check",str(p)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
            if cp.returncode!=0:errors.append(f"{p}: {cp.stderr[:300]}")
        except Exception as e:errors.append(f"{p}: {e}")
    state={"version":VERSION,"lastCheck":datetime.now().isoformat(timespec="seconds"),"files":[str(p) for p in files],"changed":[str(p) for p in changed],"backup":str(bdir) if changed else None,"errors":errors}
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    if changed:log(f"patched {len(changed)} files backup={bdir}")
    if not quiet:print(json.dumps({"ok":not errors,"targets":len(files),"changed":len(changed),"errors":errors},ensure_ascii=False,indent=2))
    return 0 if not errors else 1

def verify():
    files=targets();marked=[]
    for p in files:
        try:
            if MARK in p.read_text(encoding="utf-8",errors="ignore"):marked.append(p)
        except OSError:pass
    errors=[]
    if not marked:errors.append("AgentHub UI marker missing")
    for p in marked:
        cp=subprocess.run(["node","--check",str(p)],capture_output=True,text=True,encoding="utf-8",errors="replace")
        if cp.returncode!=0:errors.append(f"syntax error {p}: {cp.stderr[:300]}")
    print(json.dumps({"ok":not errors,"patched":len(marked),"errors":errors},ensure_ascii=False,indent=2))
    return 0 if not errors else 1

def uninstall(quiet=False):
    changed=[]
    if STATIC.is_dir():
        for p in STATIC.rglob("*.js"):
            try:s=p.read_text(encoding="utf-8",errors="ignore")
            except OSError:continue
            if MARK not in s and LEGACY_MARK not in s:continue
            n=strip_injected_ui(s)
            if n!=s:
                p.write_text(n,encoding="utf-8",newline="")
                changed.append(p)
    errors=[]
    for p in changed:
        cp=subprocess.run(["node","--check",str(p)],capture_output=True,text=True,encoding="utf-8",errors="replace")
        if cp.returncode!=0:errors.append(f"syntax error {p}: {cp.stderr[:300]}")
    if not quiet:print(json.dumps({"ok":not errors,"removed":len(changed),"errors":errors},ensure_ascii=False,indent=2))
    return 0 if not errors else 1

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--verify",action="store_true");ap.add_argument("--uninstall",action="store_true");ap.add_argument("--quiet",action="store_true");args=ap.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    if args.verify:return verify()
    if args.uninstall:return uninstall(args.quiet)
    return ensure_patch(args.quiet)

if __name__=="__main__":
    raise SystemExit(main())
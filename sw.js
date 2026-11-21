/* Electo service worker (branch portable-dev). Keeps the page, the data files it has opened, the fonts, the offline
   AI's code, and everything saved with "Save site data for offline use" (AI settings), so the site and the offline
   AI keep working without internet. Model weights and kernels, wherever they come from, are kept by the offline AI
   library itself (its own browser cache), so the worker leaves them alone. Copied to the site root by qa/mksite.sh; registered only outside claude.ai. */
const SHELL='electo-shell-v1', DATA='electo-data-v1', CDN='electo-cdn-v1', AI='electo-ai-v2'; // v2: the AI manifest is no longer kept forever
self.addEventListener('install',e=>e.waitUntil((async()=>{
  // the offline AI's code and kernels the site hosts: saved on the first visit, while the viewer is online
  try{const r=await fetch(new URL('vendor/ai-manifest.json',self.registration.scope).href,{cache:'no-cache'}); if(r.ok){const m=await r.json(), c=await caches.open(AI);
    const files=[].concat(m.lib||[]); for(const f of files){try{const u=new URL(f,self.registration.scope).href+(m.version?'?v='+encodeURIComponent(m.version):''); /* the page asks for the library by its version */ if(!(await c.match(u))){const x=await fetch(u); if(x.ok)await c.put(u,x)}}catch(e){}}}}catch(e){}
  self.skipWaiting();
})()));
self.addEventListener('activate',e=>e.waitUntil((async()=>{
  const keep=[SHELL,DATA,CDN,AI]; for(const k of await caches.keys())if(k.startsWith('electo-')&&!keep.includes(k))await caches.delete(k);
  await self.clients.claim();
})()));
const scope=()=>self.registration.scope;
self.addEventListener('fetch',e=>{
  const r=e.request; if(r.method!=='GET')return;
  const u=new URL(r.url);
  if(u.origin===self.location.origin){
    if(!r.url.startsWith(scope())||u.pathname.endsWith('/sw.js'))return;
    const rel=r.url.slice(scope().length).split('#')[0];
    if(r.mode==='navigate'||rel===''||rel.startsWith('index.html')||rel.startsWith('?')){e.respondWith(shell(r));return}
    if(rel.startsWith('pipeline/')||rel==='offline.json'){e.respondWith(data(e));return}
    if(rel.startsWith('models/')||rel.startsWith('vendor/web-llm/libs/'))return; // weights and kernels: the offline AI library keeps its own copy, so the worker does not keep a second one
    if(rel.split('?')[0]==='vendor/ai-manifest.json'){e.respondWith(fresh(r,AI));return} // which models this deploy hosts: changes with every deploy
    if(rel.startsWith('vendor/')){e.respondWith(keepFirst(r,AI));return}
    return;
  }
  if(/^(fonts\.googleapis\.com|fonts\.gstatic\.com|esm\.run|cdn\.jsdelivr\.net|unpkg\.com)$/.test(u.hostname))e.respondWith(keepFirst(r,CDN));
});
async function shell(r){ // the page: network first (revalidated, so a refresh shows a new release at once), the saved copy when offline
  const c=await caches.open(SHELL), key=scope();
  try{const res=await fetch(r.url.split('#')[0],{cache:'no-cache',credentials:'same-origin'}); if(res&&res.ok&&res.type==='basic')await c.put(key,res.clone()); return res}
  catch(x){return (await c.match(key))||(await c.match(key+'index.html'))||Response.error()}
}
async function data(e){ // data files: the network first (a revalidation, cheap when nothing changed), so a refresh shows new data at
  // once; the saved copy when offline or when the network has not answered within a few seconds
  const r=e.request, c=await caches.open(DATA), key=r.url.split('#')[0].split('?')[0];
  const net=fetch(r.url,{cache:'no-cache',credentials:'same-origin'}).then(async res=>{if(res&&res.ok)await c.put(key,res.clone()); return res}).catch(()=>null);
  const slow=new Promise(ok=>setTimeout(()=>ok('slow'),4000)), first=await Promise.race([net,slow]);
  if(first&&first!=='slow'&&first.ok)return first;
  const hit=await c.match(key); if(hit){if(first==='slow')e.waitUntil(net); return hit}
  return (await net)||new Response(JSON.stringify({error:'offline'}),{status:503,headers:{'content-type':'application/json'}});
}
async function keepFirst(r,name){ // versioned files (fonts, the AI's code, kernels and weights): kept once fetched
  const c=await caches.open(name), key=r.url.split('#')[0], hit=await c.match(key); if(hit)return hit;
  const res=await fetch(r); if(res&&(res.ok||res.type==='opaque'))await c.put(key,res.clone()); return res;
}
async function fresh(r,name){ // the network when it answers, else the saved copy
  const c=await caches.open(name), key=r.url.split('#')[0].split('?')[0];
  try{const res=await fetch(r,{cache:'no-cache'}); if(res&&res.ok)await c.put(key,res.clone()); return res}
  catch(x){return (await c.match(key))||Response.error()}
}

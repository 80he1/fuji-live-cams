const V='lc-v21',SHELL=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','apple-touch-icon.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const r=e.request,u=new URL(r.url);if(r.method!=='GET')return;
  if(/(^|\.)(youtube\.com|youtube-nocookie\.com|ytimg\.com|googlevideo\.com|ggpht\.com)$/.test(u.hostname))return; // never cache YouTube
  const same=u.origin===location.origin;if(same&&/live\.json$/.test(u.pathname))return; // always network
  if(same&&/(catalog|xtnow)\.json$/.test(u.pathname)){e.respondWith(fetch(r).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put(r,c));}return res;}).catch(()=>caches.match(r)));return;} // network-first (auto-updated by the box)
  if(r.mode==='navigate'||(same&&/\/(index\.html)?$/.test(u.pathname))){ // network-first so deploys update
    e.respondWith(fetch(r,{cache:'no-store'}).then(res=>{if(res.ok){const c=res.clone();caches.open(V).then(x=>x.put('index.html',c));}return res;}).catch(()=>caches.match('index.html')));return;}
  if((same&&/\.(png|webmanifest|json)$/.test(u.pathname))||/^fonts\.(googleapis|gstatic)\.com$/.test(u.hostname)){ // cache-first for icons & fonts
    e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{if(res.ok||res.type==='opaque'){const c=res.clone();caches.open(V).then(x=>x.put(r,c));}return res;})));}
});
self.addEventListener('message',e=>{if(e.data==='skip')self.skipWaiting();});

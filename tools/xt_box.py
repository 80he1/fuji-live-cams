#!/usr/bin/env python3
"""Box-side world extremes -> xtnow.json (same shape as the client's XT). Paced batches, retry on 429."""
import json,sys,time,urllib.request,os
D=sys.argv[1] if len(sys.argv)>1 else '.'
G=json.load(open(os.path.join(D,'grid.json')));P=json.load(open(os.path.join(D,'extremes.json')))
pts=[{'lat':p[0],'lon':p[1],'ci':p[2],'k':'g'} for p in G['pts']]+[{'lat':p[1],'lon':p[2],'cur':p,'k':'c'} for p in P]+[{'lat':90,'lon':0,'k':'np'},{'lat':-90,'lon':0,'k':'sp'}]
def q(a):
  u='https://api.open-meteo.com/v1/forecast?latitude='+','.join('%.2f'%p['lat'] for p in a)+'&longitude='+','.join('%.2f'%p['lon'] for p in a)+'&current=temperature_2m&timezone=auto'
  for t in range(4):
    try:
      j=json.load(urllib.request.urlopen(u,timeout=60));j=j if isinstance(j,list) else [j]
      for x,p in zip(j,a):
        if x and x.get('current'):p['v']=x['current']['temperature_2m'];p['off']=x.get('utc_offset_seconds',0)
      return
    except Exception as e:print('retry',t,e,file=sys.stderr);time.sleep(20*(t+1))
for i in range(0,len(pts),300):q(pts[i:i+300]);time.sleep(3)
ok=[p for p in pts if p.get('v') is not None and p['k'] not in('np','sp')]
if len(ok)<len(pts)*0.6:sys.exit('too few points')
lo=min(ok,key=lambda p:p['v']);hi=max(ok,key=lambda p:p['v'])
def sub(w):
  r=[]
  for dy in range(-2,3):
    for dx in range(-2,3):
      if not dx and not dy:continue
      la=w['lat']+dy
      if abs(la)>89.5:continue
      r.append({'lat':la,'lon':((w['lon']+dx+540)%360)-180,'ci':w.get('ci'),'k':'gc' if w['k']=='c' else 'g','cur':w.get('cur')})
  return r
s=sub(lo)+sub(hi);time.sleep(3);q(s)
for p in s:
  if p.get('v') is None:continue
  if p['v']<lo['v']:lo=p
  if p['v']>hi['v']:hi=p
pk=lambda o:o and {k:o.get(k) for k in('lat','lon','v','off','k','ci','cur')}
XT={'lo':pk(lo),'hi':pk(hi),'np':pk(next(p for p in pts if p['k']=='np')),'sp':pk(next(p for p in pts if p['k']=='sp'))}
o=os.path.join(D,'xtnow.json');json.dump({'at':int(time.time()*1000),'v':XT},open(o+'.tmp','w'),ensure_ascii=False,separators=(',',':'));os.replace(o+'.tmp',o)
print('xt',lo['v'],hi['v'])

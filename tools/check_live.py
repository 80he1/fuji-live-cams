#!/usr/bin/env python3
"""Check every cam; replace dead stream IDs with the channel's current live (best title match); write live.json.
Inputs: camidx.json {key:{ch,hint,name}}  (key = baked video id)
Output: live.json {updated, cams:{key:{v,s,t}}}  s = live|off"""
import json,re,subprocess,sys,time,difflib,concurrent.futures as cf,os
IDX=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'camidx.json'))
OUT=sys.argv[2] if len(sys.argv)>2 else 'live.json'
try:prev=json.load(open(OUT))['cams']
except Exception:prev={}
YT=['yt-dlp','--no-warnings','--skip-download','--socket-timeout','20']
def probe(v):
  r=subprocess.run(YT+['--print','%(live_status)s\t%(playable_in_embed)s\t%(title)s','https://www.youtube.com/watch?v='+v],capture_output=True,text=True,timeout=120)
  o=r.stdout.strip().split('\t')
  if len(o)<3:
    e=r.stderr
    return {'ok':False,'blocked':('Sign in to confirm' in e or 'HTTP Error 429' in e),'title':''}
  return {'ok':o[0]=='is_live' and o[1]!='False','title':o[2],'blocked':False}
def lives(ch):
  r=subprocess.run(YT+['--flat-playlist','--playlist-end','40','--print','%(id)s\t%(live_status)s\t%(title)s',(f'https://www.youtube.com/channel/{ch}' if ch.startswith('UC') else ch.rstrip('/'))+'/streams'],capture_output=True,text=True,timeout=180)
  out=[]
  for l in r.stdout.splitlines():
    p=l.split('\t')
    if len(p)==3 and p[1]=='is_live':out.append((p[0],p[2]))
  return out
norm=lambda s:re.sub(r'[\d\-:/\.年月日時分\s【】\[\]()（）|｜]+',' ',(s or '').lower()).strip()
def sim(a,b):return difflib.SequenceMatcher(None,norm(a),norm(b)).ratio()
now=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
res={};blocked=0
def cur(k):return (prev.get(k) or {}).get('v') or k
keys=list(IDX)
with cf.ThreadPoolExecutor(3) as ex:
  pr=dict(zip(keys,ex.map(lambda k:probe(cur(k)),keys)))
  for k in [k for k in keys if pr[k]['blocked']]:
    time.sleep(3);pr[k]=probe(cur(k))
  # also try the baked id if override died
  bad=[k for k in keys if not pr[k]['ok'] and cur(k)!=k]
  for k,p in zip(bad,ex.map(probe,bad)):
    if p['ok']:pr[k]=p;prev.setdefault(k,{})['v']=k
blocked=sum(p['blocked'] for p in pr.values())
if blocked>len(keys)*.3:
  print('BLOCKED',blocked);sys.exit(3)
for k in keys:
  if pr[k]['ok']:res[k]={'v':cur(k),'s':'live','t':now}
need={}
for k in keys:
  if k not in res and IDX[k].get('ch'):need.setdefault(IDX[k]['ch'],[]).append(k)
with cf.ThreadPoolExecutor(2) as ex:
  chl=dict(zip(need,ex.map(lambda c:lives(c),need)))
used={r['v'] for r in res.values()}
rep=0
for ch,ks in need.items():
  cands=[c for c in chl[ch] if c[0] not in used]
  pairs=sorted(((max(sim(IDX[k].get('hint'),t),sim(IDX[k].get('name'),t)),k,v,t) for k in ks for v,t in cands),reverse=True)
  done=set()
  for s,k,v,t in pairs:
    if k in done or v in used:continue
    if s<0.45 and not(len(ks)==1 and len(cands)==1 and s>=0.2):continue
    p=probe(v)
    if not p['ok']:continue
    res[k]={'v':v,'s':'live','t':now,'m':round(s,2)};used.add(v);done.add(k);rep+=1
for k in keys:
  if k not in res:res[k]={'v':cur(k),'s':'off','t':now}
n=sum(r['s']=='live' for r in res.values())
new={'updated':now,'cams':res}
old=None
try:old=json.load(open(OUT))
except Exception:pass
same=old and {k:(v['v'],v['s']) for k,v in old['cams'].items()}=={k:(v['v'],v['s']) for k,v in res.items()}
if not same or not old:json.dump(new,open(OUT,'w'),ensure_ascii=False,separators=(',',':'))
print(f'live {n}/{len(keys)} replaced {rep} off {len(keys)-n} changed {not same}')

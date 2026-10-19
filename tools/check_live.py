#!/usr/bin/env python3
"""Rolling, budgeted live check -> live.json (merged; unchecked cams keep their last state).
Inputs: camidx.json {key:{ch,hint,name}} (key = baked video id), tools/channels.json (registry)
Output: live.json {updated, cams:{key:{v,s,t,m?}}, add}   s = live|off ; t = time this cam was last checked
Per run (~hourly):
 0. guard: exit if YouTube back-off active; after a back-off exactly ONE probe request must pass first.
 1. light pass (i.ytimg.com thumbnails, CDN, not rate-limited): rolling 1/4 of cams by persisted cursor;
    a 404 thumbnail = video deleted/private -> that cam becomes due for a heavy check now.
 2. priority queue: each cam has a re-check interval (off 2h growing to 12h, recently swapped 4h, registry 6h,
    live 8h, stable live >24h 18h); the most overdue go first, at most HEAVY_CAP heavy probes per run.
 3. heavy probe = ONE watch-page fetch (no cookies), sequential, jittered 3-8 s pauses; stop at the first block.
 4. dead cam -> replacement candidates from channel RSS (light) by title similarity; channel /streams listing
    (heavy, yt-dlp) only as rare fallback (per channel <= every 12h, <= STREAMS_CAP per run).
 5. registry channels: RSS each run for new streams; /streams once a day per channel (rotating).
Never writes live.json on a block. State: /workspace/disco/live_state.json (not committed)."""
import json,re,sys,time,difflib,os,random,urllib.request,urllib.error,subprocess
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ytguard as G
E=lambda k,d:float(os.environ.get(k,d))
HEAVY_CAP=int(E('HEAVY_CAP',24));STREAMS_CAP=int(E('STREAMS_CAP',2));RSS_CAP=int(E('RSS_CAP',30));LIGHT_FRAC=E('LIGHT_FRAC',0.25)
MIN_GAP=E('LIVE_MIN_GAP',3300)       # run at most ~hourly even if the loop calls more often
H=3600;IV={'off':2*H,'swap':4*H,'add':6*H,'live':8*H,'stable':18*H}
PZ=(E('PAUSE_MIN',3),E('PAUSE_MAX',8))
ST=os.environ.get('LIVE_STATE','/workspace/disco/live_state.json')
def log(*a):print('[live]',*a,flush=True)
now=time.time();NOW=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now))
try:S=json.load(open(ST))
except Exception:S={}
for k,d in (('k',{}),('ch',{}),('add',{}),('cur',0),('last',0)):S.setdefault(k,d)
def save():os.makedirs(os.path.dirname(ST),exist_ok=True);json.dump(S,open(ST+'.tmp','w'),separators=(',',':'));os.replace(ST+'.tmp',ST)
if G.blocked():log('BACKOFF (YouTube block) until',G.hm(G.backoff()),'- live.json untouched');sys.exit(0)
if now-S['last']<MIN_GAP and not os.environ.get('LIVE_FORCE'):log('last run',G.hm(S['last']),'<',int(MIN_GAP/60),'min ago -> skip');sys.exit(0)
IDX=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'camidx.json'))
OUT=sys.argv[2] if len(sys.argv)>2 else 'live.json'
try:old=json.load(open(OUT))
except Exception:old={}
prev=old.get('cams',{});prevadd=old.get('add',{})
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
if os.environ.get('LIVE_FAKE'):
  import importlib.util as iu;sp=iu.spec_from_file_location('fake',os.environ['LIVE_FAKE']);F=iu.module_from_spec(sp);sp.loader.exec_module(F);http=F.http;sleep=lambda s:None
else:
  sleep=time.sleep
  def http(url,head=False,to=25):
    rq=urllib.request.Request(url,method='HEAD' if head else 'GET',headers={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.8'})
    try:
      with urllib.request.urlopen(rq,timeout=to) as r:return r.status,('' if head else r.read().decode('utf-8','replace'))
    except urllib.error.HTTPError as e:return e.code,''
    except Exception as e:return -1,str(e)
CNT={'thumb':0,'rss':0,'heavy':0,'streams':0}
class Blocked(Exception):pass
# ---------- light endpoints ----------
def thumb(v):                       # i.ytimg.com CDN: 404 => video removed/private (cannot tell live vs ended)
  CNT['thumb']+=1;c,_=http(f'https://i.ytimg.com/vi/{v}/hqdefault.jpg',head=True);sleep(0.2+random.random()*0.4);return c
RSSOFF=[False]
def rss(ch):                        # channel uploads feed (newest 15, includes stream entries)
  if RSSOFF[0] or CNT['rss']>=RSS_CAP or not ch.startswith('UC') or not G.allow('live'):return None
  CNT['rss']+=1;G.spend(1,'live-rss');c,b=http('https://www.youtube.com/feeds/videos.xml?channel_id='+ch);sleep(1.5+random.random()*1.5)
  if c in(403,429):RSSOFF[0]=True;log('rss',c,'-> no more rss this run');return None
  if c!=200:return None
  S['ch'].setdefault(ch,{})['rss']=now
  return [(m.group(1),re.sub(r'&amp;','&',m.group(2))) for m in re.finditer(r'<yt:videoId>([\w-]{11})</yt:videoId>.*?<title>([^<]*)</title>',b,re.S)]
# ---------- heavy: one watch-page fetch ----------
def HEAVY_CAP_ADJ():
  global HEAVY_CAP;HEAVY_CAP=min(HEAVY_CAP,CNT['heavy']+8)
UNK=[0];MODE=[os.environ.get('LIVE_HEAVY','watch')]
def ytdlp(v):                       # fallback probe (~3 requests): used only if watch pages cannot be parsed
  G.spend(2,'live')
  if os.environ.get('LIVE_FAKE'):return F.ytdlp(v)
  try:r=subprocess.run(['yt-dlp','--no-warnings','--skip-download','--socket-timeout','20','--print','%(live_status)s\t%(playable_in_embed)s\t%(title)s','https://www.youtube.com/watch?v='+v],capture_output=True,text=True,timeout=120)
  except subprocess.TimeoutExpired:return {'s':'unk','title':''}
  o=r.stdout.strip().split('\t')
  if len(o)<3:
    if G.is_block(r.stderr):raise Blocked('yt-dlp')
    return {'s':'gone' if 'unavailable' in r.stderr.lower() or 'private' in r.stderr.lower() else 'unk','title':''}
  return {'s':'live' if o[0]=='is_live' and o[1]!='False' else 'off','title':o[2]}
def heavy(v):
  """-> {'s': live|off|gone|unk, 'title'}; raises Blocked"""
  if CNT['heavy']>=HEAVY_CAP or not G.allow('live'):return None
  CNT['heavy']+=1;G.spend(1,'live');sleep(PZ[0]+random.random()*(PZ[1]-PZ[0]))
  if MODE[0]=='ytdlp':
    r=ytdlp(v);UNK[0]=UNK[0]+1 if r['s']=='unk' else 0;return r
  c,b=http(f'https://www.youtube.com/watch?v={v}&hl=en&bpctr=9999999999&has_verified=1')
  if c==429:raise Blocked('http 429')
  m=re.search(r'ytInitialPlayerResponse\s*=\s*\{',b)
  if c==200 and m:
    try:pr,_=json.JSONDecoder().raw_decode(b,m.end()-1)
    except Exception:pr=None
  else:pr=None
  if pr is None:
    if c==200 and ('Sign in to confirm' in b or 'not a bot' in b or '/sorry/' in b):raise Blocked('bot-check page')
    UNK[0]+=1
    if c==200 and MODE[0]=='watch':MODE[0]='ytdlp';HEAVY_CAP_ADJ();log('watch page not parseable -> yt-dlp probes for this run (cap reduced)');r=ytdlp(v);UNK[0]=0 if r['s']!='unk' else UNK[0];return r
    return {'s':'unk','title':'','c':c}
  ps=pr.get('playabilityStatus',{});st=ps.get('status','');rs=str(ps.get('reason',''))+json.dumps(ps.get('errorScreen',''))[:400]
  if st=='LOGIN_REQUIRED' and ('bot' in rs or 'Sign in to confirm' in rs):raise Blocked('LOGIN_REQUIRED bot-check')
  vd=pr.get('videoDetails',{});lb=pr.get('microformat',{}).get('playerMicroformatRenderer',{}).get('liveBroadcastDetails',{})
  UNK[0]=0
  if st in('ERROR','UNPLAYABLE') or (st=='LOGIN_REQUIRED'):return {'s':'gone','title':vd.get('title','')}
  live=(vd.get('isLive') is True or lb.get('isLiveNow') is True) and ps.get('playableInEmbed',True) is not False and st=='OK'
  return {'s':'live' if live else 'off','title':vd.get('title','')}
def streams(ch):                    # heavy fallback listing (yt-dlp flat playlist ~2 requests)
  if CNT['streams']>=STREAMS_CAP or not G.allow('live',2):return []
  if now-S['ch'].get(ch,{}).get('st',0)<12*H:return []
  CNT['streams']+=1;G.spend(2,'live-streams');S['ch'].setdefault(ch,{})['st']=now;sleep(PZ[0]+random.random()*(PZ[1]-PZ[0]))
  u=(f'https://www.youtube.com/channel/{ch}' if ch.startswith('UC') else ch.rstrip('/'))+'/streams'
  if os.environ.get('LIVE_FAKE'):return F.streams(ch)
  try:r=subprocess.run(['yt-dlp','--no-warnings','--flat-playlist','--playlist-end','30','--print','%(id)s\t%(live_status)s\t%(title)s',u],capture_output=True,text=True,timeout=120)
  except subprocess.TimeoutExpired:return []
  if G.is_block(r.stderr):raise Blocked('streams')
  return [(p[0],p[2]) for p in (l.split('\t') for l in r.stdout.splitlines()) if len(p)==3 and p[1]=='is_live']
norm=lambda s:re.sub(r'[\d\-:/\.年月日時分\s【】\[\]()（）|｜]+',' ',(s or '').lower()).strip()
def sim(a,b):return difflib.SequenceMatcher(None,norm(a),norm(b)).ratio()
# ---------- state / priority ----------
def cur(k):return (prev.get(k) or {}).get('v') or k
def tparse(t):
  import calendar
  try:return calendar.timegm(time.strptime(t,'%Y-%m-%dT%H:%M:%SZ'))
  except Exception:return 0
for k in IDX:                       # migrate: seed from live.json
  if k not in S['k']:
    p=prev.get(k);S['k'][k]={'lc':tparse(p['t']) if p else 0,'ok':bool(p and p['s']=='live'),'since':tparse(p['t']) if p and p['s']=='live' else 0,'f':0 if not p or p['s']=='live' else 1,'sw':0}
for k in list(S['k']):
  if k not in IDX:S['k'].pop(k)
def interval(k):
  s=S['k'][k]
  if s.get('due'):return 0
  if not s['ok']:return min(IV['off']*2**max(s['f']-1,0),12*H)
  if now-s.get('sw',0)<48*H:return IV['swap']
  if s.get('since') and now-s['since']>24*H:return IV['stable']
  return IV['live']
def score(k):
  iv=interval(k);s=S['k'][k]
  return 99 if iv==0 else (now-s['lc'])/iv
res={k:dict(prev[k]) for k in IDX if k in prev}   # merge base: unchecked cams keep last state
used={r['v'] for r in res.values()}
def mark(k,v,s,m=None):
  st=S['k'][k];st['lc']=now;st.pop('due',None)
  if s=='live':
    if not st['ok'] or res.get(k,{}).get('v')!=v:st['since']=now
    if res.get(k,{}).get('v') not in(None,v):st['sw']=now
    st['ok']=True;st['f']=0
  else:st['ok']=False;st['f']=st.get('f',0)+1;st['since']=0
  e={'v':v,'s':s,'t':NOW}
  if m is not None:e['m']=m
  elif s=='live' and res.get(k,{}).get('v')==v and 'm' in res.get(k,{}):e['m']=res[k]['m']
  res[k]=e;used.add(v)
stat={'live':0,'off':0,'rep':0,'gone':0,'unk':0}
try:
  # 0. single probe after a back-off
  if G.need_probe():
    pk=max((k for k in IDX if S['k'][k]['ok']),key=lambda k:now-S['k'][k].get('since',now) if S['k'][k].get('since') else 0,default=next(iter(IDX)))
    r=heavy(cur(pk));log('probe after back-off:',cur(pk),r and r['s'])
    if r is None or r['s']=='unk':log('probe inconclusive -> stop (no write)');S['last']=now;save();sys.exit(0)
    G.probe_ok();mark(pk,cur(pk),'live' if r['s']=='live' else 'off');stat[r['s']]=stat.get(r['s'],0)+1
  G.live_start()
  # 1. light pass (rolling cursor)
  keys=sorted(IDX);n=max(1,int(len(keys)*LIGHT_FRAC+0.999));c0=S['cur']%len(keys)
  for k in (keys+keys)[c0:c0+n]:
    c=thumb(cur(k))
    if c==404:S['k'][k]['due']=404
  S['cur']=(c0+n)%len(keys)
  for k in IDX:
    if k not in prev:S['k'][k]['due']=1      # new cam
  # 2-3. heavy checks by priority
  q=sorted((k for k in IDX if score(k)>=1),key=score,reverse=True)
  dead=[]
  for k in q:
    if CNT['heavy']>=HEAVY_CAP:break
    v=cur(k)
    if S['k'][k].get('due')==404:stat['gone']+=1;dead.append((k,'gone'));continue   # thumbnail gone: skip the heavy probe
    r=heavy(v)
    if r is None:break
    if r['s']=='unk':
      stat['unk']+=1
      if UNK[0]>=3:log('3 unparseable watch pages in a row -> stop heavy checks');break
      continue
    if r['s']=='live':mark(k,v,'live');stat['live']+=1
    else:stat[r['s']]+=1;dead.append((k,r['s']))
  # 4. replacements for dead cams: baked id, then channel RSS candidates, then (rarely) /streams
  for k,why in dead:
    found=None;ch=IDX[k].get('ch') or ''
    if cur(k)!=k and k not in used and thumb(k)==200:
      r=heavy(k)
      if r and r['s']=='live':found=(k,None)
    if not found and ch:
      for src in(rss,streams):
        if found:break
        L=src(ch) or []
        cands=sorted(((max(sim(IDX[k].get('hint'),t),sim(IDX[k].get('name'),t)),v,t) for v,t in L if v not in used and v!=cur(k)),reverse=True)
        ks=[x for x in IDX if (IDX[x].get('ch')==ch)]
        for s,v,t in cands[:2]:
          if s<0.45 and not(len(ks)==1 and s>=0.2):continue
          r=heavy(v)
          if r is None:break
          if r['s']=='live':found=(v,round(s,2));break
    if found:mark(k,found[0],'live',found[1]);stat['rep']+=1
    else:mark(k,cur(k),'off')
  # 5. channel registry
  add={};REG=os.path.join(os.path.dirname(os.path.abspath(__file__)),'channels.json')
  try:reg=json.load(open(REG))
  except Exception:reg={'channels':[]}
  dk=[x.lower() for x in reg.get('deny_kw',[])];di=set(reg.get('deny_ids',[]))
  known=set(IDX)|used
  for v,e in prevadd.items():                # keep previous additions; re-verify on a 6h schedule
    a=S['add'].setdefault(v,{'lc':now})
    if now-a['lc']>=IV['add'] and CNT['heavy']<HEAVY_CAP:
      r=heavy(v)
      if r and r['s']!='unk':
        a['lc']=now
        if r['s']!='live':S['add'].pop(v,None);continue
    add[v]=dict(e);known.add(v)
  chs=reg.get('channels',[]);day=int(now//H)%max(len(chs),1)
  for i,chn in enumerate(chs):
    L=(rss(chn['ch']) or []) if i%2==int(now//H)%2 else []   # each registry channel's RSS every ~2nd run
    if i==day:L+=streams(chn['ch'])          # one channel per run gets the heavier listing (~every 11h each)
    for v,t in L:
      tl=(t or '').lower()
      if v in known or v in di or v in add or any(x in tl for x in dk+[y.lower() for y in chn.get('deny_kw',[])]):continue
      for rl in chn.get('rules',[]):
        if any(x.lower() in tl for x in rl['kw']):
          known.add(v);r=heavy(v)
          if r and r['s']=='live':
            e={x:rl[x] for x in('name','en','lat','lon','utc','side') if x in rl};e['theme']=rl.get('theme',chn.get('theme'));e.setdefault('side',chn.get('side',''));e['ch']=chn['ch']
            if 'utc' not in e and 'utc' in chn:e['utc']=chn['utc']
            nn=sum(1 for x in add.values() if x.get('_r')==id(rl))
            if nn:e['name']+=f' {nn+1}';e['en']=e.get('en','')+f' {nn+1}'
            e['_r']=id(rl);add[v]=e;S['add'][v]={'lc':now}
          break
  for e in add.values():e.pop('_r',None)
except Blocked as b:
  t=G.note_block('check_live');G.live_end();S['last']=now;save()
  log('BLOCKED (',b,') after',CNT,'-> back off until',G.hm(t),'- live.json untouched');sys.exit(3)
new={'updated':NOW,'cams':{k:res[k] for k in IDX if k in res},'add':add}
same=old and {k:(v['v'],v['s']) for k,v in old.get('cams',{}).items()}=={k:(v['v'],v['s']) for k,v in new['cams'].items()} and old.get('add',{})==add
if not same:json.dump(new,open(OUT,'w'),ensure_ascii=False,separators=(',',':'))
S['last']=now;save();G.live_end()
nl=sum(r['s']=='live' for r in new['cams'].values())
log(f"checked {stat} | requests {CNT} | www last hour {G.used()} | live {nl}/{len(IDX)} add {len(add)} | changed {not same} | cursor {S['cur']}")

"""Shared YouTube request guard for check_live.py and disco.py (state: /workspace/disco/yt_guard.json).
- A bot-check / 429 seen by either tool sets a back-off for both. Back-off grows 1h -> 2h -> 4h -> 6h for blocks
  within 24h of the previous one (level resets after a clean 24h).
- After a back-off ends, the guard is in 'probe' state: exactly ONE probe request (check_live) must succeed before
  full work resumes; discovery stays paused until then.
- Global hourly request budget (sliding 1h window) shared by both; discovery gets only a small slice and only
  while check_live is idle. check_live has priority."""
import json,os,time
P=os.environ.get('YTGUARD','/workspace/disco/yt_guard.json')
LEVELS=[1,2,4,6]                                   # hours
HOUR_BUDGET=int(os.environ.get('YT_HOUR_BUDGET','70'))   # heavy www.youtube.com requests per rolling hour (all tools)
DISCO_BUDGET=int(os.environ.get('YT_DISCO_BUDGET','12')) # of which discovery may use at most
def _l():
  try:return json.load(open(P))
  except Exception:return {}
def _s(d):
  os.makedirs(os.path.dirname(P) or '.',exist_ok=True);json.dump(d,open(P+'.tmp','w'));os.replace(P+'.tmp',P)
def is_block(err):
  e=err or '';return 'Sign in to confirm' in e or 'HTTP Error 429' in e or 'Too Many Requests' in e or 'rate-limit' in e.lower() or 'not a bot' in e
def note_block(src):
  d=_l();now=time.time();rep=now-d.get('last_block',0)<24*3600
  lv=min(d.get('lvl',-1)+1,len(LEVELS)-1) if rep else 0
  d['lvl']=lv;d['backoff']=now+LEVELS[lv]*3600;d['last_block']=now;d['n']=d.get('n',0)+1;d['src']=src;d['probe']=1;_s(d);return d['backoff']
def backoff():return _l().get('backoff',0)
def blocked():return time.time()<backoff()
def need_probe():return bool(_l().get('probe'))
def probe_ok():d=_l();d['probe']=0;d['probe_ok']=time.time();_s(d)
def last_block():return _l().get('last_block',0)
def spend(n=1,src='live'):
  d=_l();now=time.time();r=[x for x in d.get('req',[]) if now-x[0]<3600];r.append([round(now),src,n]);d['req']=r;_s(d)
def used(src=None):
  now=time.time();return sum(x[2] for x in _l().get('req',[]) if now-x[0]<3600 and (src is None or x[1]==src))
def allow(src='live',n=1):
  if blocked():return False
  if src=='disco':
    if need_probe() or live_recent(600):return False
    return used('disco')+n<=DISCO_BUDGET and used()+n<=HOUR_BUDGET
  return used()+n<=HOUR_BUDGET
def live_start():d=_l();d['live_start']=time.time();_s(d)
def live_end():d=_l();d['live_end']=time.time();_s(d)
def live_recent(sec=600):
  d=_l();s,e=d.get('live_start',0),d.get('live_end',0);now=time.time()
  return (s>e and now-s<3600) or now-e<sec   # running (stale-start guard 1h) or finished <sec ago
def hm(t):return time.strftime('%m-%d %H:%M',time.localtime(t))

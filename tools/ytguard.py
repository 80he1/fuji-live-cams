"""Shared YouTube request guard for check_live.py and disco.py (state: /workspace/disco/yt_guard.json).
A bot-check / 429 seen by either tool sets a back-off for both; check_live has priority over discovery."""
import json,os,time
P=os.environ.get('YTGUARD','/workspace/disco/yt_guard.json')
def _l():
  try:return json.load(open(P))
  except Exception:return {}
def _s(d):
  os.makedirs(os.path.dirname(P),exist_ok=True);json.dump(d,open(P+'.tmp','w'));os.replace(P+'.tmp',P)
def is_block(err):
  e=err or '';return 'Sign in to confirm' in e or 'HTTP Error 429' in e or 'Too Many Requests' in e or 'rate-limit' in e.lower()
def note_block(src):
  d=_l();now=time.time();rep=now-d.get('last_block',0)<12*3600
  d['backoff']=now+(6 if rep else 3)*3600;d['last_block']=now;d['n']=d.get('n',0)+1;d['src']=src;_s(d);return d['backoff']
def backoff():
  return _l().get('backoff',0)
def last_block():return _l().get('last_block',0)
def live_start():d=_l();d['live_start']=time.time();_s(d)
def live_end():d=_l();d['live_end']=time.time();_s(d)
def live_recent(sec=600):
  d=_l();s,e=d.get('live_start',0),d.get('live_end',0);now=time.time()
  return (s>e and now-s<3600) or now-e<sec   # running (stale-start guard 1h) or finished <10 min ago
def hm(t):return time.strftime('%m-%d %H:%M',time.localtime(t))

#!/usr/bin/env python3
"""WorldSeer mass discovery (box loop). Incremental & polite:
 each run: a few live-filtered YouTube searches + channel /streams mining -> new ids; probe a budgeted batch
 (live, embeddable, formats, viewers, desc); filter junk; geocode (GeoNames cities15000); theme by keywords;
 recheck known channels (alive rate); thumbnail sharpness/brightness/frozen; score -> tier S/A/B/C; write catalog.json.
 Stops the run and backs off on bot-check / 429. State: /workspace/disco/state.json (not committed)."""
import json,re,os,sys,time,subprocess,unicodedata,math,random,io,urllib.request,hashlib
T0=time.time();BUDGET=float(os.environ.get('DISCO_BUDGET','540'))
D='/workspace/disco';ST=os.path.join(D,'state.json');OUT=sys.argv[1] if len(sys.argv)>1 else 'catalog.json'
YT=['yt-dlp','--no-warnings','--socket-timeout','20']
def log(*a):print('[disco]',*a,flush=True)
import fcntl
os.makedirs(D,exist_ok=True);LK=open(os.path.join(D,'.lock'),'w')
try:fcntl.flock(LK,fcntl.LOCK_EX|fcntl.LOCK_NB)
except OSError:log('another run in progress, skip');sys.exit(0)
def left():return BUDGET-(time.time()-T0)
try:S=json.load(open(ST))
except Exception:S={}
S.setdefault('cams',{});S.setdefault('seen',{});S.setdefault('qi',0);S.setdefault('chs',{});S.setdefault('backoff',0);S.setdefault('stats',{})
def save():json.dump(S,open(ST+'.tmp','w'),ensure_ascii=False,separators=(',',':'));os.replace(ST+'.tmp',ST)
if time.time()<S['backoff']:log('backing off until',time.strftime('%H:%M',time.localtime(S['backoff'])));sys.exit(0)
BLOCK=[False]
def run(args,to=120):
  r=subprocess.run(YT+args,capture_output=True,text=True,timeout=to)
  e=r.stderr
  if 'Sign in to confirm' in e or 'HTTP Error 429' in e or 'rate-limit' in e.lower():
    BLOCK[0]=True;S['backoff']=time.time()+2*3600;S['stats']['blocks']=S['stats'].get('blocks',0)+1;log('BLOCKED by YouTube -> back off 2h')
  return r.stdout
# ---------- queries ----------
TH={'fuji':['富士山','mt fuji','mount fuji'],'koyo':['紅葉','autumn leaves'],'okinawa':['沖縄','okinawa','石垣','宮古'],'yakei':['夜景','night view','skyline'],
 'umi':['beach','harbor','harbour','port ','marina','surf','ocean','海','港','ビーチ','bay'],'doubutsu':['zoo','animal','nest','eagle','osprey','bird','cat ','dog','panda','動物','鳥','猫','犬'],
 'volcano':['volcano','火山','eruption','噴火'],'onsen':['温泉','onsen','hot spring'],'sakana':['aquarium','reef','fish','水族館','水槽','underwater'],
 'airport':['airport','空港','plane spotting','runway'],'train':['train','railcam','railway','railroad','鉄道','電車','駅','新幹線','station cam'],
 'bridge':['bridge','橋'],'snow':['ski','snow','スキー','雪'],'star':['aurora','northern lights','night sky','meteor','オーロラ','星空','stars'],
 'safari':['safari','waterhole','africam','wildlife'],'cross':['crossing','street','square','交差点','街','plaza','downtown','times square']}
BASE=['live cam','webcam','live camera 24/7','ライブカメラ','livecam','live stream camera','cámara en vivo','webcam live','câmera ao vivo','caméra en direct','live webcam','실시간 카메라','实时摄像头']
def queries():
  q=[]
  for b in BASE[:6]:q.append(b)
  for th,ks in TH.items():
    for k in ks[:3]:q.append(f'{k.strip()} live cam' if re.match(r'[a-z]',k) else f'{k} ライブカメラ')
  try:
    cs=[l.split('\t') for l in open(os.path.join(D,'cities15000.txt'),encoding='utf-8')];cs.sort(key=lambda x:-int(x[14] or 0))
    for c in cs[:1500]:q.append(f'{c[1]} live cam')
  except Exception:pass
  return q
# ---------- gazetteer ----------
STOPW=set('live cam camera webcam beach bay port harbor harbour ocean sea river lake mountain park city town island station street bridge zoo airport hotel resort view north south east west new old san santa saint st de la el le los las the of and victoria union china japan sun moon star stars praia playa plage strand spiaggia aurora mustang deer cat dog bird eagle wildlife nature centre center lincoln jackson franklin washington'.split())
GZ=None
try:EN=set(w.strip() for w in list(open(os.path.join(D,'en10k.txt')))[:2500])
except Exception:EN=set()
def SJ(a):
  try:a.encode('shift_jis');return True
  except Exception:return False
def gaz():
  global GZ
  if GZ is not None:return GZ
  lat={};cjk={}
  for l in open(os.path.join(D,'cities15000.txt'),encoding='utf-8'):
    x=l.rstrip('\n').split('\t');pop=int(x[14] or 0);la,lo,cc=float(x[4]),float(x[5]),x[8]
    ja=None
    alts=[a for a in x[3].split(',') if a]
    ja=next((a for a in alts if re.search(r'[\u3040-\u30ff]',a) and not re.search(r'[\uac00-\ud7af]',a)),None)
    if cc=='JP':
      kj=[a for a in alts if re.fullmatch(r'[\u3040-\u30ff\u4e00-\u9fff]{2,}',a) and SJ(a)]
      kj2=[a for a in kj if re.fullmatch(r'[\u4e00-\u9fff]+',a)]
      if kj2:ja=min(kj2,key=len)
      elif kj:ja=min(kj,key=len)
    for a in alts:
      if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',a):
        if len(a)>=2:
          o=cjk.get(a)
          if not o or pop>o[3]:cjk[a]=(x[2],la,lo,pop,cc,ja)
    pr={x[2].lower(),x[1].lower()}
    for nm in pr|({a.lower() for a in alts if re.fullmatch(r"[A-Za-z][A-Za-z .'\-]{3,}",a)} if pop>=500000 else set()):
      k=re.sub(r'\s+',' ',re.sub(r"[^a-z0-9' \-]",'',unicodedata.normalize('NFKD',nm).encode('ascii','ignore').decode().lower().replace('-',' ') if re.fullmatch(r'[\x00-\u024f ]+',nm) else nm)).strip()
      if len(k)<4 or k in STOPW:continue
      if pop<200000 and all(w in EN for w in k.split()):continue
      w=pop if nm in pr else pop*0.7
      for kk in {k,re.sub(r'^st ','saint ',k),re.sub(r'^saint ','st ',k)}:
        o=lat.get(kk)
        if not o or w>o[6]:lat[kk]=(x[1] if re.fullmatch(r'[\x00-\u024f\u1e00-\u1eff ]+',x[1]) else x[2],la,lo,pop,cc,ja,w)
  try:
    for f in os.listdir('.'):
      if not f.endswith('.json') or f in('live.json','catalog.json','camidx.json'):continue
      try:A=json.load(open(f))
      except Exception:continue
      if not isinstance(A,list):continue
      for c in A:
        if not isinstance(c,dict) or c.get('lat') is None:continue
        j=(c.get('name') or '').split(' ')[0];e=(c.get('en') or '').split(' ')[0]
        if re.fullmatch(r'[\u3040-\u30ff\u4e00-\u9fff]{2,}',j) and j not in cjk:cjk[j]=(e or j,c['lat'],c['lon'],50000,'JP' if c.get('side') in('日本','') or 'UTC+9'==c.get('utc') else '',j)
  except Exception:pass
  GZ=(lat,cjk);return GZ
CN={};CAP={}
for l in open(os.path.join(D,'countryInfo.txt'),encoding='utf-8'):
  if l.startswith('#'):continue
  x=l.split('\t')
  if len(x)>5:
    CAP[x[0]]=x[5].lower()
    if x[4].lower() not in ('jersey','georgia','chad','niger','jordan','turkey','guinea','mali','oman','peru','cuba','china','dominica','monaco','panama','colombia','victoria'):CN[x[4].lower()]=x[0]
REG={k:v for k,v in {
 'bali':('Bali',-8.65,115.22,'ID','バリ島'),'hawaii':('Hawaii',21.3,-157.85,'US','ハワイ'),'maui':('Maui',20.8,-156.33,'US','マウイ島'),'oahu':('Oahu',21.47,-157.98,'US','オアフ島'),
 'waikiki':('Waikiki',21.28,-157.83,'US','ワイキキ'),'phuket':('Phuket',7.88,98.39,'TH','プーケット'),'santorini':('Santorini',36.42,25.43,'GR','サントリーニ島'),'mykonos':('Mykonos',37.45,25.33,'GR','ミコノス島'),
 'ibiza':('Ibiza',38.98,1.43,'ES','イビサ島'),'maldives':('Maldives',4.17,73.51,'MV','モルディブ'),'okinawa':('Okinawa',26.21,127.68,'JP','沖縄'),'hokkaido':('Hokkaido',43.06,141.35,'JP','北海道'),
 'alaska':('Alaska',61.22,-149.9,'US','アラスカ'),'yellowstone':('Yellowstone',44.46,-110.83,'US','イエローストーン'),'niagara falls':('Niagara Falls',43.08,-79.07,'CA','ナイアガラの滝'),'niagara':('Niagara Falls',43.08,-79.07,'CA','ナイアガラの滝'),
 'grand canyon':('Grand Canyon',36.06,-112.14,'US','グランドキャニオン'),'times square':('Times Square',40.758,-73.985,'US','タイムズスクエア'),'venice':('Venice',45.437,12.336,'IT','ヴェネツィア'),'venezia':('Venice',45.437,12.336,'IT','ヴェネツィア'),
 'lapland':('Lapland',66.5,25.73,'FI','ラップランド'),'iceland':('Iceland',64.15,-21.94,'IS','アイスランド'),'tenerife':('Tenerife',28.29,-16.63,'ES','テネリフェ島'),'mallorca':('Mallorca',39.57,2.65,'ES','マヨルカ島'),'majorca':('Mallorca',39.57,2.65,'ES','マヨルカ島'),
 'gran canaria':('Gran Canaria',27.92,-15.6,'ES','グラン・カナリア島'),'zermatt':('Zermatt',46.02,7.75,'CH','ツェルマット'),'matterhorn':('Matterhorn',45.98,7.66,'CH','マッターホルン'),'jungfrau':('Jungfrau',46.54,7.96,'CH','ユングフラウ'),
 'chamonix':('Chamonix',45.92,6.87,'FR','シャモニー'),'mont blanc':('Mont Blanc',45.83,6.86,'FR','モンブラン'),'st. maarten':('Sint Maarten',18.04,-63.11,'SX','セント・マーチン'),'sint maarten':('Sint Maarten',18.04,-63.11,'SX','セント・マーチン'),'maho beach':('Sint Maarten',18.04,-63.11,'SX','セント・マーチン'),
 'key west':('Key West',24.56,-81.78,'US','キーウェスト'),'florida':('Florida',27.95,-82.46,'US','フロリダ'),'starbase':('Starbase',25.99,-97.16,'US','スターベース'),'aruba':('Aruba',12.52,-70.03,'AW','アルバ'),'bahamas':('Bahamas',25.04,-77.35,'BS','バハマ'),
 'tahiti':('Tahiti',-17.65,-149.43,'PF','タヒチ'),'fiji':('Fiji',-18.14,178.44,'FJ','フィジー'),'cancun':('Cancún',21.16,-86.85,'MX','カンクン'),'etna':('Etna',37.75,14.99,'IT','エトナ山'),'kilauea':('Kīlauea',19.41,-155.28,'US','キラウエア'),
 'mount fuji':('Mount Fuji',35.36,138.73,'JP','富士山'),'fuji':('Mount Fuji',35.36,138.73,'JP','富士山'),'lake tahoe':('Lake Tahoe',39.1,-120.03,'US','タホ湖'),'everest':('Everest',27.99,86.93,'NP','エベレスト'),'svalbard':('Svalbard',78.22,15.65,'NO','スヴァールバル'),
 'dolomites':('Dolomites',46.41,11.84,'IT','ドロミテ'),'amalfi':('Amalfi',40.63,14.6,'IT','アマルフィ'),'positano':('Positano',40.63,14.48,'IT','ポジターノ'),'cinque terre':('Cinque Terre',44.13,9.71,'IT','チンクエ・テッレ'),'lake como':('Lake Como',45.99,9.26,'IT','コモ湖'),
}.items()}
CC2={'US':['usa','u.s.',' nyc',' new york','new hampshire','new jersey','new mexico','north carolina','south carolina','north dakota','south dakota','rhode island','west virginia']+[' alabama', ' alaska', ' arizona', ' arkansas', ' california', ' colorado', ' connecticut', ' delaware', ' florida', ' georgia', ' hawaii', ' idaho', ' illinois', ' indiana', ' iowa', ' kansas', ' kentucky', ' louisiana', ' maine', ' maryland', ' massachusetts', ' michigan', ' minnesota', ' mississippi', ' missouri', ' montana', ' nebraska', ' nevada', ' ohio', ' oklahoma', ' oregon', ' pennsylvania', ' tennessee', ' texas', ' utah', ' vermont', ' virginia', ' wisconsin', ' wyoming'],'BR':['brasil','brazil'],'MX':['mexico'],'ES':['espana','spain'],'PH':['philippines'],'TH':['thailand'],'ID':['indonesia'],'NZ':['new zealand'],'GB':[' uk ','england','scotland','wales'],'JP':['japan','日本'],'IT':['italia'],'DE':['deutschland'],'ES':['españa'],'FR':[' france'],'NL':['nederland'],'AU':['australia','queensland','new south wales','victoria, au','tasmania'],'CA':['canada','ontario','quebec','british columbia','alberta','newfoundland','nova scotia','manitoba']}
def geo(text,minpop=0):
  lat,cjk=gaz();t=unicodedata.normalize('NFKC',text);tl=t.lower();best=None
  toks=re.findall(r"[a-z0-9][a-z0-9'\-]*",unicodedata.normalize('NFKD',tl).encode('ascii','ignore').decode().replace('.','').replace('-',' '))
  cc1={CN[c] for c in CN if re.search(r'(?<![a-z])'+re.escape(c)+r'(?![a-z])',tl)};cch=cc1|{c for c,ks in CC2.items() if any(k in tl for k in ks)}
  for n in (3,2,1):
    for i in range(len(toks)-n+1):
      k=' '.join(toks[i:i+n]);v=lat.get(k)
      if k in REG:v=REG[k]+(10**9,);v=(v[0],v[1],v[2],10**7,v[3],v[4],10**9)
      if v and v[3]>=minpop:
        sc=(n,v[6]*(3 if cch and v[4] in cch else 1))
        if best is None or sc>best[0]:best=(sc,v)
  for seg in re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]{2,}',t):
    for L in range(min(6,len(seg)),1,-1):
      for i in range(len(seg)-L+1):
        w=seg[i:i+L];v=cjk.get(w)
        if v and re.fullmatch(r'[\u30a0-\u30ff]+',w) and (len(w)<3 or (i>0 and re.match(r'[\u30a0-\u30ff]',seg[i-1])) or (i+L<len(seg) and re.match(r'[\u30a0-\u30ff]',seg[i+L]))):v=None
        if v and v[3]>=minpop:
          suf=i+L<len(seg) and seg[i+L] in '市町村区駅郡'
          sc=(L+1+(2 if suf else 0),v[3])
          if best is None or sc>best[0]:best=(sc,v)
  if cc1 and (best is None or best[1][4] not in cch):
    for c0 in sorted(cc1):
      v=lat.get(CAP.get(c0,''))
      if v and v[4]==c0:return v
  return best[1] if best else None
# ---------- filters ----------
BAD=re.compile(r"music|lofi|lo-fi|\bbgm\b|beats|piano|jazz|chill|relax|sleep|asmr|meditat|ambien|white noise|gaming|minecraft|fortnite|roblox|gta|vtuber|歌枠|雑談|作業用|podcast|interview|talk show|sermon|worship|replay|rerun|highlights|compilation|best of|walking tour|\bwalk\b|walks|driving|drive|bike ride|\bride\b|散歩|ドライブ|vlog|crypto|bitcoin|giveaway|\$|trading|forex|stock market|radio|karaoke|news live|breaking|ニュース|速報|election|debate|war |missile|osint|multi.?cam|rolling cam|cams around|webcams around|top \d+|earth now|world live|\d+ cams|24/7 live cameras|movie|anime|cartoon|kids|tv channel|live tv|channel live|sports|football|soccer|nba|nfl|match|race|mlb|horse racing|bingo|lottery|casino|slot|prayer live|quran|qur'an|tarot|horoscope|protest|coverage|rally|launch|church|mass |service|sunday|press conference|parliament|senate|court|hearing|cnbc|tv18|\bnews\b|lofi|scanner|police|fire dispatch|walkthru|walkthrough|walk thru|unveil|claims|reaction|elon|musk|tesla|trump|biden|putin|gaza|israel|ukraine|iran|podcast|q&a|\bama\b|giveaway|subscribe|shorts|watch party|watchalong|reacts?\b|cameras around|around the world|\btour\b|tracker|earthquake map|monitor\b|radar|停電|防災情報|storm chas|very long stream|satellites?\b|flight ?radar|\bscanner",re.I)
BADCH=re.compile(r"news|\btv\b|cnbc|bbc|cnn|fox|sky news|abc|nbc|cbs|al jazeera|dw |france 24|reuters|church|ministr|gaming|music|records",re.I)
CAMW=re.compile(r"cam|camera|カメラ|webcam|ライブ|live|実況|直播|라이브|в прямом|en vivo|ao vivo|en direct",re.I)
def junk(title,desc,ch):
  if BAD.search(title or ''):return 'kw'
  if not CAMW.search((title or '')+' '+(desc or '')[:300]):return 'nocam'
  if BADCH.search(ch or '') and not re.search(r'cam|webcam|weather',ch or '',re.I):return 'ch'
  return None
def theme(text):
  tl=' '+unicodedata.normalize('NFKC',text).lower()+' ';best=None;bn=0
  for th,ks in TH.items():
    n=sum(1 for k in ks if (re.search(r'(?<![a-z])'+re.escape(k.strip().lower())+r'(?![a-z])',tl) if re.match(r'[a-z]',k) else k in tl))
    if n>bn:best,bn=th,n
  return best
# ---------- thumbnail quality ----------
def thumb(v):
  try:
    from PIL import Image,ImageFilter,ImageStat
    b=urllib.request.urlopen(f'https://i.ytimg.com/vi/{v}/hqdefault_live.jpg?{int(time.time())}',timeout=15).read()
    im=Image.open(io.BytesIO(b)).convert('L').resize((160,90))
    br=ImageStat.Stat(im).mean[0];ed=ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES)).mean[0]
    h=''.join('1' if p>br else '0' for p in list(im.resize((8,8)).tobytes()))
    return {'br':round(br,1),'ed':round(ed,1),'h':h}
  except Exception:return None
# ---------- probe ----------
def probe(v):
  o=run(['-j','--skip-download','https://www.youtube.com/watch?v='+v],150)
  try:j=json.loads(o.splitlines()[-1])
  except Exception:return None
  hs=[f.get('height') or 0 for f in j.get('formats',[]) if f.get('vcodec')!='none'];fp=[f.get('fps') or 0 for f in j.get('formats',[]) if f.get('vcodec')!='none']
  return {'live':j.get('live_status')=='is_live','emb':j.get('playable_in_embed')!=False,'t':j.get('title',''),'d':(j.get('description') or '')[:600],
          'ch':j.get('channel_id'),'chn':j.get('channel') or j.get('uploader') or '','vw':j.get('concurrent_view_count') or 0,'h':max(hs or [0]),'fps':max(fp or [0])}
def score(c):
  h=c.get('h',0);s={2160:40,1440:35,1080:28,720:18}.get(h,40 if h>2160 else 8)
  if c.get('fps',0)>=50:s+=5
  s+=min(20,6*math.log10(1+c.get('vw',0)))
  chk=max(1,c.get('k',1));s+=20*c.get('a',1)/chk
  q=c.get('q') or {}
  if q:s+=min(8,q.get('ed',0)/2.5)+(2 if 25<q.get('br',0)<230 else 0)
  if c.get('fr',0)>=3:s-=15
  if c.get('cur'):s+=5
  return round(s,1)
def tier(s):return 'S' if s>=75 else 'A' if s>=60 else 'B' if s>=45 else 'C'
def clean(t):
  t=unicodedata.normalize('NFKC',t);t=re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF]','',t)
  t=re.sub(r'【[^】]*(live|ライブ|LIVE)[^】]*】|\[[^\]]*(live|LIVE)[^\]]*\]|\(?(24/7|4K|HD|LIVE|Live|live|ライブ配信|ライブカメラ|ライブ|Webcam|webcam|Live Cam|live cam|Live Camera|livestream|Livestream)\)?','',t)
  t=re.sub(r'【\s*】|\[\s*\]|\(\s*\)','',t);t=re.sub(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}.*$|\s*[|｜/／–-]\s*$','',t);t=re.sub(r'\s+',' ',t).strip(' -|｜/:・')
  return t[:60]
def classify(c):
  rt=c.get('rt') or c['t'];rd=c.get('rd','');gz_ok=os.path.exists(os.path.join(D,'cities15000.txt'))
  if junk(rt,rd,c.get('chn','')):return False
  g=(geo(rt) or geo(c.get('chn','')+' '+rd,100000)) if gz_ok else None
  c['th']=theme(rt+' '+rd[:200]) or ''
  for k in('p','pj','la','lo','cc'):c.pop(k,None)
  if g:c.update({'p':g[0],'pj':g[5] or '','la':round(g[1],3),'lo':round(g[2],3),'cc':g[4]})
  return True
# ---------- run ----------
known=set()
try:
  for c in json.load(open('camidx.json')):known.add(c)
except Exception:pass
try:
  for k,v in json.load(open('live.json')).get('cams',{}).items():known.add(v.get('v'))
except Exception:pass
Q=queries();new=[]
nq=int(os.environ.get('DISCO_Q','5'))
for _ in range(nq):
  if BLOCK[0] or left()<200:break
  q=Q[S['qi']%len(Q)];S['qi']+=1
  o=run(['--flat-playlist','--playlist-end','100','--print','%(id)s\t%(live_status)s\t%(channel_id)s\t%(title)s','https://www.youtube.com/results?search_query='+urllib.parse.quote(q) if False else 'https://www.youtube.com/results?search_query='+q.replace(' ','+')+'&sp=EgJAAQ%3D%3D'],120)
  n=0
  for l in o.splitlines():
    p=l.split('\t')
    if len(p)<4 or p[1]!='is_live':continue
    v=p[0]
    if v in S['seen'] or v in known:continue
    S['seen'][v]={'t':p[3][:120],'ch':p[2],'q':q};n+=1
    if p[2] and p[2]!='NA':S['chs'].setdefault(p[2],{'last':0})
  log('search',repr(q),'new',n);time.sleep(3+random.random()*3)
save()
# channel mining + recheck (cheap: /streams flat listing gives live status)
byc={}
for v,c in S['cams'].items():byc.setdefault(c.get('cid'),[]).append(v)
chs=sorted(S['chs'].items(),key=lambda x:x[1].get('last',0))[:int(os.environ.get('DISCO_CH','12'))]
for ch,meta in chs:
  if BLOCK[0] or left()<150:break
  o=run(['--flat-playlist','--playlist-end','60','--print','%(id)s\t%(live_status)s\t%(title)s',f'https://www.youtube.com/channel/{ch}/streams'],120)
  meta['last']=time.time();live=set()
  for l in o.splitlines():
    p=l.split('\t')
    if len(p)>=3 and p[1]=='is_live':
      live.add(p[0])
      if p[0] not in S['seen'] and p[0] not in known:S['seen'][p[0]]={'t':p[2][:120],'ch':ch,'q':'ch'}
  for v in byc.get(ch,[]):
    c=S['cams'][v];c['k']=c.get('k',1)+1
    if v in live:c['a']=c.get('a',1)+1;c['ls']=time.time()
  time.sleep(2+random.random()*2)
save()
# probe a batch of unprobed ids
todo=[v for v,s in S['seen'].items() if not s.get('p')]
random.shuffle(todo);np_=0;acc=0
gz_ok=os.path.exists(os.path.join(D,'cities15000.txt'))
for v in todo[:int(os.environ.get('DISCO_P','50'))]:
  if BLOCK[0] or left()<60:break
  s=S['seen'][v];pre=junk(s['t'],'',''if True else '')
  if pre=='kw':s['p']='junk';continue
  r=probe(v);np_+=1;time.sleep(1.5+random.random()*2)
  if BLOCK[0]:break
  if not r:s['p']='err';continue
  if not r['live'] or not r['emb']:s['p']='off' if not r['live'] else 'noemb';continue
  j=junk(r['t'],r['d'],r['chn'])
  if j:s['p']='junk:'+j;continue
  c={'t':clean(r['t']) or r['t'][:60],'rt':r['t'][:160],'rd':r['d'][:300],'cid':r['ch'],'chn':r['chn'][:40],'vw':r['vw'],'h':r['h'],'fps':r['fps'],'k':1,'a':1,'ls':time.time()}
  classify(c)
  c['q']=thumb(v);S['cams'][v]=c;s['p']='ok';acc+=1
  if r['ch']:S['chs'].setdefault(r['ch'],{'last':time.time()})
  if acc%10==0:save()
# thumbnail refresh for a slice (frozen detection)
for v in sorted(S['cams'],key=lambda v:S['cams'][v].get('qt',0))[:30]:
  if left()<20:break
  c=S['cams'][v];q=thumb(v);c['qt']=time.time()
  if q:
    if c.get('q') and c['q'].get('h')==q['h']:c['fr']=c.get('fr',0)+1
    else:c['fr']=0
    c['q']=q
save()
# catalog
now=time.time();rows=[]
for v,c in S['cams'].items():
  if now-c.get('ls',0)>2*86400:continue
  if not classify(c):continue
  sc=score(c);c['s']=sc
  rows.append([v,c['t'],c.get('p',''),c.get('pj',''),c.get('la'),c.get('lo'),c.get('cc',''),c.get('th',''),tier(sc),c.get('h',0),c.get('chn',''),int(c.get('vw',0))])
rows.sort(key=lambda r:'SABC'.index(r[8]))
cat={'v':int(now),'f':['id','t','p','pj','la','lo','cc','th','tier','h','ch','vw'],'c':rows}
json.dump(cat,open(OUT+'.tmp','w'),ensure_ascii=False,separators=(',',':'));os.replace(OUT+'.tmp',OUT)
from collections import Counter
log(f'probed {np_} accepted {acc} seen {len(S["seen"])} cams {len(S["cams"])} catalog {len(rows)} tiers {dict(Counter(r[8] for r in rows))} pending {len([1 for s in S["seen"].values() if not s.get("p")])} t={int(time.time()-T0)}s')

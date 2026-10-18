#!/usr/bin/env python3
"""Build srdict.json: the lazily-loaded intent dictionary for the search sheet (themes, keywords, countries,
continents, Japanese regions/prefectures/cities with readings, world cities, live conditions) + curated cam country map."""
import json,os,math
H=os.path.dirname(os.path.abspath(__file__));R=os.path.dirname(H);D='/workspace/disco'
L=['ja','en','zh-Hans','zh-Hant','ko','th','vi','id','es','fr','de','pt','it','ru','ar','hi']
I=json.load(open(os.path.join(R,'i18n.json')))
TH={ # extra synonyms (theme names in all 16 languages are added automatically)
'fuji':'富士山 富士 ふじさん ふじ fuji mtfuji mt fuji mount fuji fujisan 후지산',
'koyo':'紅葉 もみじ こうよう 黄葉 秋 autumn leaves foliage fall colors fall foliage autumn colours 단풍 枫叶 红叶 楓葉 follaje otono feuillage herbstlaub laub folhagem foliage autunnale осень листва',
'okinawa':'沖縄 おきなわ okinawa 石垣 宮古 那覇 ryukyu',
'yakei':'夜景 やけい night view night views skyline cityscape night city 야경 景色 vista nocturna vue de nuit nachtansicht',
'umi':'海 うみ 港 みなと ビーチ 浜 海岸 海辺 beach beaches ocean sea harbor harbour port bay coast marina surf 바다 해변 海滩 海灘 playa plage strand praia spiaggia mare mar море пляж ทะเล biển pantai',
'doubutsu':'動物 どうぶつ 生き物 animal animals zoo wildlife 동물 动物 動物園 animales animaux tiere animais animali животные สัตว์',
'world':'世界 世界の街 world city cities 都市 とし 街 まち',
'volcano':'火山 かざん 噴火 volcano volcanoes eruption 화산 火山口 volcan vulkan vulcao vulcano вулкан',
'onsen':'温泉 おんせん 温泉街 onsen hot spring hot springs 온천 温泉 aguas termales source chaude therme',
'sakana':'魚 さかな 水族館 すいぞくかん 水中 aquarium fish underwater reef coral 수족관 水族馆 acuario aquarium',
'airport':'空港 くうこう 飛行機 ひこうき airport airports plane planes airplane aviation runway plane spotting 공항 机场 機場 aeropuerto aeroport flughafen aeroporto аэропорт',
'train':'電車 でんしゃ 鉄道 てつどう 新幹線 しんかんせん 駅 えき 列車 train trains railway railroad rail shinkansen station 기차 열차 火车 列车 tren gare zug bahn trem treno поезд',
'bridge':'橋 はし bridge bridges 다리 桥 puente pont brucke ponte мост',
'cross':'交差点 こうさてん 街角 まちかど 通り 繁華街 crossing intersection street streets downtown square plaza 거리 街道 calle rue strasse',
'snow':'雪 ゆき 雪山 スキー すきー スキー場 降雪 ski skiing snow snowing ski resort 눈 스키 雪 nieve neige schnee neve снег',
'star':'星 ほし 星空 ほしぞら 天の川 オーロラ おーろら stars star starry night sky milky way aurora northern lights 별 极光 estrellas etoiles sterne aurora boreal',
'safari':'サファリ さふぁり アフリカ safari africa savanna savannah waterhole 사파리',
'asahi':'朝日 あさひ 日の出 ひので sunrise dawn 일출 日出 amanecer lever du soleil sonnenaufgang nascer do sol alba восход',
'yuhi':'夕日 ゆうひ 夕焼け ゆうやけ 夕陽 日の入り sunset dusk 일몰 日落 atardecer coucher du soleil sonnenuntergang por do sol tramonto закат'}
KW=[ # object keywords matched in titles (fall back to their theme when nothing matches)
['cat','🐱','doubutsu',{'ja':'猫','en':'Cats'},'猫 ねこ ネコ にゃんこ 子猫 cat cats kitten kitty 고양이 猫咪 gato gatos chat chats katze katzen gatto кот кошка แมว mèo kucing'],
['dog','🐶','doubutsu',{'ja':'犬','en':'Dogs'},'犬 いぬ イヌ 子犬 dog dogs puppy puppies 강아지 狗 perro chien hund cachorro cane собака'],
['panda','🐼','doubutsu',{'ja':'パンダ','en':'Pandas'},'パンダ ぱんだ panda pandas 판다 熊猫 熊貓'],
['penguin','🐧','doubutsu',{'ja':'ペンギン','en':'Penguins'},'ペンギン ぺんぎん penguin penguins 펭귄 企鹅 pinguino manchot pinguin'],
['bird','🐦','doubutsu',{'ja':'鳥','en':'Birds'},'鳥 とり 野鳥 bird birds feeder birdcam nest eagle osprey owl falcon hawk 새 鸟 pajaro oiseau vogel'],
['bear','🐻','doubutsu',{'ja':'クマ','en':'Bears'},'クマ くま 熊 bear bears grizzly 곰'],
['elephant','🐘','safari',{'ja':'ゾウ','en':'Elephants'},'ゾウ ぞう 象 elephant elephants 코끼리'],
['giraffe','🦒','doubutsu',{'ja':'キリン','en':'Giraffes'},'キリン きりん giraffe giraffes'],
['shinkansen','🚄','train',{'ja':'新幹線','en':'Shinkansen'},'新幹線 しんかんせん shinkansen bullet train'],
['plane','✈️','airport',{'ja':'飛行機','en':'Planes'},'飛行機 ひこうき plane planes airplane aircraft runway plane spotting'],
['ship','🚢','umi',{'ja':'船','en':'Ships'},'船 ふね 客船 フェリー ship ships ferry boat boats cruise port'],
['tower','🗼','yakei',{'ja':'タワー','en':'Towers'},'タワー たわー tower 東京タワー スカイツリー skytree eiffel'],
['castle','🏯','world',{'ja':'城','en':'Castles'},'城 しろ castle castles'],
['lake','🏞️','',{'ja':'湖','en':'Lakes'},'湖 みずうみ lake lakes 호수 lago lac see'],
['river','🌊','',{'ja':'川','en':'Rivers'},'川 かわ 河川 river rivers 강 rio fleuve fluss'],
['mountain','⛰️','',{'ja':'山','en':'Mountains'},'山 やま 山岳 mountain mountains peak alps alpine 산 montana montagne berg'],
]
def tri(ja,en,**o):d={'ja':ja,'en':en};d.update(o);return d
CONT={
'EU':(tri('ヨーロッパ','Europe',**{'zh-Hans':'欧洲','zh-Hant':'歐洲','ko':'유럽','th':'ยุโรป','vi':'Châu Âu','id':'Eropa','es':'Europa','fr':'Europe','de':'Europa','pt':'Europa','it':'Europa','ru':'Европа','ar':'أوروبا','hi':'यूरोप'}),'欧州 よーろっぱ おうしゅう eu'),
'AS':(tri('アジア','Asia',**{'zh-Hans':'亚洲','zh-Hant':'亞洲','ko':'아시아','th':'เอเชีย','vi':'Châu Á','id':'Asia','es':'Asia','fr':'Asie','de':'Asien','pt':'Ásia','it':'Asia','ru':'Азия','ar':'آسيا','hi':'एशिया'}),'あじあ'),
'NA':(tri('北米','North America',**{'zh-Hans':'北美洲','zh-Hant':'北美洲','ko':'북아메리카','th':'อเมริกาเหนือ','vi':'Bắc Mỹ','id':'Amerika Utara','es':'Norteamérica','fr':'Amérique du Nord','de':'Nordamerika','pt':'América do Norte','it':'Nord America','ru':'Северная Америка','ar':'أمريكا الشمالية','hi':'उत्तरी अमेरिका'}),'ほくべい 北アメリカ 北米大陸 north american'),
'SA':(tri('南米','South America',**{'zh-Hans':'南美洲','zh-Hant':'南美洲','ko':'남아메리카','th':'อเมริกาใต้','vi':'Nam Mỹ','id':'Amerika Selatan','es':'Sudamérica','fr':'Amérique du Sud','de':'Südamerika','pt':'América do Sul','it':'Sud America','ru':'Южная Америка','ar':'أمريكا الجنوبية','hi':'दक्षिण अमेरिका'}),'なんべい 南アメリカ 中南米 latin america latam'),
'OC':(tri('オセアニア','Oceania',**{'zh-Hans':'大洋洲','zh-Hant':'大洋洲','ko':'오세아니아','th':'โอเชียเนีย','vi':'Châu Đại Dương','id':'Oseania','es':'Oceanía','fr':'Océanie','de':'Ozeanien','pt':'Oceania','it':'Oceania','ru':'Океания','ar':'أوقيانوسيا','hi':'ओशिनिया'}),'おせあにあ 南太平洋'),
'AF':(tri('アフリカ','Africa',**{'zh-Hans':'非洲','zh-Hant':'非洲','ko':'아프리카','th':'แอฟริกา','vi':'Châu Phi','id':'Afrika','es':'África','fr':'Afrique','de':'Afrika','pt':'África','it':'Africa','ru':'Африка','ar':'أفريقيا','hi':'अफ़्रीका'}),'あふりか'),
'AN':(tri('南極','Antarctica',**{'zh-Hans':'南极洲','zh-Hant':'南極洲','ko':'남극','th':'แอนตาร์กติกา','vi':'Nam Cực','id':'Antarktika','es':'Antártida','fr':'Antarctique','de':'Antarktis','pt':'Antártida','it':'Antartide','ru':'Антарктида','ar':'القارة القطبية الجنوبية','hi':'अंटार्कटिका'}),'なんきょく antarctic'),
}
# country aliases (Intl.DisplayNames supplies names in all 16 UI languages at runtime)
CAL={'US':'米国 べいこく アメリカ あめりか アメリカ合衆国 usa us america united states states 美國 美国 미국','GB':'英国 イギリス いぎりす uk britain great britain england scotland wales 영국','JP':'日本 にほん にっぽん japan nippon nihon 일본 日本国 japon japao giappone япония',
 'KR':'韓国 かんこく 대한민국 한국 korea south korea','CN':'中国 ちゅうごく 中华人民共和国 china','TW':'台湾 たいわん 臺灣 taiwan','DE':'ドイツ どいつ deutschland germany','FR':'フランス ふらんす france','IT':'イタリア いたりあ italia italy',
 'ES':'スペイン すぺいん espana spain','PT':'ポルトガル portugal','NL':'オランダ holland netherlands nederland','CH':'スイス schweiz suisse switzerland','AT':'オーストリア osterreich austria','RU':'ロシア россия russia',
 'BR':'ブラジル brasil brazil','MX':'メキシコ mexico','CA':'カナダ canada','AU':'オーストラリア 豪州 australia aussie','NZ':'ニュージーランド new zealand nz','TH':'タイ王国 ประเทศไทย thailand','VN':'ベトナム viet nam vietnam',
 'ID':'インドネシア indonesia','PH':'フィリピン philippines','IN':'インド india bharat','AE':'アラブ首長国連邦 uae','IS':'アイスランド iceland island','NO':'ノルウェー norway norge','SE':'スウェーデン sweden sverige','FI':'フィンランド finland suomi',
 'GR':'ギリシャ greece hellas','TR':'トルコ turkiye turkey','NP':'ネパール nepal','ZA':'南アフリカ south africa','KE':'ケニア kenya','AR':'アルゼンチン argentina','CL':'チリ chile','PE':'ペルー peru','CZ':'チェコ czechia czech republic','PL':'ポーランド polska poland','IE':'アイルランド ireland','HR':'クロアチア croatia hrvatska'}
JR=[ # Japanese regions (bbox s,w,n,e)
['北海道','Hokkaido','ほっかいどう hokkaido',[41.3,139.3,45.6,146.0]],['東北','Tohoku','とうほく tohoku 東北地方',[36.8,139.0,41.6,142.2]],['関東','Kanto','かんとう kanto 関東地方 首都圏',[34.8,138.4,37.2,141.0]],
['中部','Chubu','ちゅうぶ chubu 中部地方',[34.5,135.8,38.6,139.9]],['北陸','Hokuriku','ほくりく hokuriku',[35.3,135.4,38.6,139.9]],['甲信越','Koshinetsu','こうしんえつ koshinetsu',[35.2,137.3,38.6,139.9]],
['東海','Tokai','とうかい tokai 東海地方',[34.5,136.2,35.8,139.2]],['関西','Kansai','かんさい kansai 近畿 きんき kinki 近畿地方',[33.4,134.2,35.8,136.9]],['中国地方','Chugoku','ちゅうごくちほう chugoku',[33.7,130.8,35.7,134.5]],
['四国','Shikoku','しこく shikoku',[32.7,132.0,34.5,134.8]],['九州','Kyushu','きゅうしゅう kyushu 九州地方',[30.9,129.5,34.0,132.1]],['南西諸島','Nansei Islands','なんせいしょとう 奄美 あまみ amami',[24.0,122.9,29.0,131.4]]]
PREF=[('北海道','ほっかいどう','Hokkaido',43.06,141.35),('青森','あおもり','Aomori',40.82,140.74),('岩手','いわて','Iwate',39.70,141.15),('宮城','みやぎ','Miyagi',38.27,140.87),('秋田','あきた','Akita',39.72,140.10),('山形','やまがた','Yamagata',38.24,140.36),('福島','ふくしま','Fukushima',37.75,140.47),
('茨城','いばらき','Ibaraki',36.34,140.45),('栃木','とちぎ','Tochigi',36.57,139.88),('群馬','ぐんま','Gunma',36.39,139.06),('埼玉','さいたま','Saitama',35.86,139.65),('千葉','ちば','Chiba',35.61,140.12),('東京','とうきょう','Tokyo',35.69,139.69),('神奈川','かながわ','Kanagawa',35.45,139.64),
('新潟','にいがた','Niigata',37.90,139.02),('富山','とやま','Toyama',36.70,137.21),('石川','いしかわ','Ishikawa',36.59,136.63),('福井','ふくい','Fukui',36.07,136.22),('山梨','やまなし','Yamanashi',35.66,138.57),('長野','ながの','Nagano',36.65,138.18),('岐阜','ぎふ','Gifu',35.39,136.72),
('静岡','しずおか','Shizuoka',34.98,138.38),('愛知','あいち','Aichi',35.18,136.91),('三重','みえ','Mie',34.73,136.51),('滋賀','しが','Shiga',35.00,135.87),('京都','きょうと','Kyoto',35.02,135.76),('大阪','おおさか','Osaka',34.69,135.52),('兵庫','ひょうご','Hyogo',34.69,135.18),
('奈良','なら','Nara',34.69,135.83),('和歌山','わかやま','Wakayama',34.23,135.17),('鳥取','とっとり','Tottori',35.50,134.24),('島根','しまね','Shimane',35.47,133.05),('岡山','おかやま','Okayama',34.66,133.93),('広島','ひろしま','Hiroshima',34.40,132.46),('山口','やまぐち','Yamaguchi',34.19,131.47),
('徳島','とくしま','Tokushima',34.07,134.56),('香川','かがわ','Kagawa',34.34,134.04),('愛媛','えひめ','Ehime',33.84,132.77),('高知','こうち','Kochi',33.56,133.53),('福岡','ふくおか','Fukuoka',33.61,130.42),('佐賀','さが','Saga',33.25,130.30),('長崎','ながさき','Nagasaki',32.74,129.87),
('熊本','くまもと','Kumamoto',32.79,130.74),('大分','おおいた','Oita',33.24,131.61),('宮崎','みやざき','Miyazaki',31.91,131.42),('鹿児島','かごしま','Kagoshima',31.56,130.56),('沖縄','おきなわ','Okinawa',26.21,127.68)]
PREF_KM={'北海道':0,'東京':45,'神奈川':40,'大阪':35,'京都':55,'沖縄':0,'長野':85,'岩手':85,'福島':80,'新潟':90,'鹿児島':90}
JC=[('札幌','さっぽろ','Sapporo',43.06,141.35,20),('函館','はこだて','Hakodate',41.77,140.73,15),('小樽','おたる','Otaru',43.19,141.0,10),('仙台','せんだい','Sendai',38.27,140.87,20),('横浜','よこはま','Yokohama',35.44,139.64,15),('鎌倉','かまくら','Kamakura',35.32,139.55,6),
('箱根','はこね','Hakone',35.23,139.05,10),('日光','にっこう','Nikko',36.75,139.6,15),('名古屋','なごや','Nagoya',35.17,136.91,20),('金沢','かなざわ','Kanazawa',36.56,136.66,12),('神戸','こうべ','Kobe',34.69,135.2,15),('広島市','ひろしまし','Hiroshima City',34.39,132.46,12),
('博多','はかた','Hakata',33.59,130.42,8),('那覇','なは','Naha',26.21,127.68,10),('石垣','いしがき','Ishigaki',24.34,124.16,25),('宮古島','みやこじま','Miyako-jima',24.8,125.28,20),('渋谷','しぶや','Shibuya',35.66,139.70,2),('新宿','しんじゅく','Shinjuku',35.69,139.70,2.5),
('浅草','あさくさ','Asakusa',35.71,139.80,2),('銀座','ぎんざ','Ginza',35.67,139.77,1.5),('お台場','おだいば','Odaiba',35.63,139.78,2.5),('秋葉原','あきはばら','Akihabara',35.70,139.77,1.5),('道頓堀','どうとんぼり','Dotonbori',34.67,135.50,1.5),('梅田','うめだ','Umeda',34.70,135.50,2),
('河口湖','かわぐちこ','Kawaguchiko',35.5,138.76,8),('別府','べっぷ','Beppu',33.28,131.49,8),('草津','くさつ','Kusatsu',36.62,138.6,6),('富良野','ふらの','Furano',43.34,142.38,20),('軽井沢','かるいざわ','Karuizawa',36.35,138.6,8),('熱海','あたみ','Atami',35.1,139.07,6),('伊豆','いず','Izu',34.85,138.95,35),('白馬','はくば','Hakuba',36.7,137.86,12)]
WC=[('パリ','Paris','ぱり',48.857,2.352),('ロンドン','London','ろんどん',51.507,-0.128),('ニューヨーク','New York','にゅーよーく nyc ny manhattan まんはったん',40.73,-73.99),('ロサンゼルス','Los Angeles','ろさんぜるす la',34.05,-118.24),
('サンフランシスコ','San Francisco','さんふらんしすこ sf',37.77,-122.42),('ラスベガス','Las Vegas','らすべがす vegas',36.17,-115.14),('シカゴ','Chicago','しかご',41.88,-87.63),('マイアミ','Miami','まいあみ',25.76,-80.19),('ホノルル','Honolulu','ほのるる',21.31,-157.86),
('ハワイ','Hawaii','はわい hawaii',20.8,-157.5,350),('シアトル','Seattle','しあとる',47.61,-122.33),('バンクーバー','Vancouver','ばんくーばー',49.28,-123.12),('トロント','Toronto','とろんと',43.65,-79.38),('ナイアガラ','Niagara Falls','ないあがら niagara',43.08,-79.07,15),
('ローマ','Rome','ろーま roma',41.9,12.5),('ヴェネツィア','Venice','べねちあ ベネチア venezia',45.44,12.33,15),('ミラノ','Milan','みらの milano',45.46,9.19),('フィレンツェ','Florence','ふぃれんつぇ firenze',43.77,11.25),('バルセロナ','Barcelona','ばるせろな',41.39,2.17),
('マドリード','Madrid','まどりーど',40.42,-3.70),('リスボン','Lisbon','りすぼん lisboa',38.72,-9.14),('アムステルダム','Amsterdam','あむすてるだむ',52.37,4.9),('ベルリン','Berlin','べるりん',52.52,13.4),('ミュンヘン','Munich','みゅんへん munchen',48.14,11.58),
('ウィーン','Vienna','うぃーん wien',48.21,16.37),('プラハ','Prague','ぷらは praha',50.08,14.43),('チューリッヒ','Zurich','ちゅーりっひ zuerich',47.38,8.54),('ストックホルム','Stockholm','すとっくほるむ',59.33,18.07),('オスロ','Oslo','おすろ',59.91,10.75),
('ヘルシンキ','Helsinki','へるしんき',60.17,24.94),('レイキャビク','Reykjavik','れいきゃびく',64.15,-21.94,60),('ドバイ','Dubai','どばい',25.2,55.27),('イスタンブール','Istanbul','いすたんぶーる',41.01,28.98),('モスクワ','Moscow','もすくわ moskva',55.76,37.62),
('ソウル','Seoul','そうる 서울',37.57,126.98),('釜山','Busan','ぷさん 부산 pusan',35.18,129.08),('北京','Beijing','ぺきん peking',39.9,116.4),('上海','Shanghai','しゃんはい',31.23,121.47),('香港','Hong Kong','ほんこん hongkong',22.3,114.17),('台北','Taipei','たいぺい',25.03,121.56),
('バンコク','Bangkok','ばんこく',13.76,100.5),('シンガポール','Singapore','しんがぽーる',1.35,103.82),('バリ島','Bali','ばりとう ばり bali',-8.4,115.19,80),('シドニー','Sydney','しどにー',-33.87,151.21),('メルボルン','Melbourne','めるぼるん',-37.81,144.96),
('オークランド','Auckland','おーくらんど',-36.85,174.76),('ケープタウン','Cape Town','けーぷたうん',-33.92,18.42),('リオデジャネイロ','Rio de Janeiro','りお rio',-22.91,-43.17),('ブエノスアイレス','Buenos Aires','ぶえのすあいれす',-34.6,-58.38),
('メキシコシティ','Mexico City','めきしこしてぃ cdmx',19.43,-99.13),('カンクン','Cancun','かんくん',21.16,-86.85),('ヴェネツィア','Venice','venice',45.44,12.33,15),('アルプス','Alps','あるぷす alps alpen',46.5,9.5,350)]
COND=[ # key, emoji, labels(16), synonyms
['day','☀️',['昼','Daytime','白天','白天','낮','กลางวัน','Ban ngày','Siang','De día','En journée','Tagsüber','De dia','Di giorno','День','نهار','दिन'],'ひる 昼間 日中 にっちゅう day daytime 白天 낮 dia jour tag giorno'],
['night','🌙',['夜','Night','夜晚','夜晚','밤','กลางคืน','Ban đêm','Malam','De noche','La nuit','Nachts','À noite','Di notte','Ночь','ليل','रात'],'よる 夜間 やかん 深夜 night nighttime 夜晚 밤 noche nuit nacht noite notte ночь'],
['rise','🌅',['朝日（いま）','Sunrise now','正在日出','正在日出','지금 일출','พระอาทิตย์ขึ้นตอนนี้','Bình minh lúc này','Matahari terbit','Amaneciendo','Lever du soleil','Sonnenaufgang jetzt','Nascer do sol','Alba ora','Рассвет сейчас','شروق الآن','अभी सूर्योदय'],'朝日 あさひ 日の出 ひので sunrise dawn 일출 日出 amanecer lever sonnenaufgang alba восход'],
['set','🌇',['夕日（いま）','Sunset now','正在日落','正在日落','지금 일몰','พระอาทิตย์ตกตอนนี้','Hoàng hôn lúc này','Matahari terbenam','Atardeciendo','Coucher du soleil','Sonnenuntergang jetzt','Pôr do sol','Tramonto ora','Закат сейчас','غروب الآن','अभी सूर्यास्त'],'夕日 ゆうひ 夕焼け ゆうやけ 夕陽 日の入り sunset dusk 일몰 日落 atardecer coucher sonnenuntergang tramonto закат'],
['clear','☀️',['晴れ','Clear sky','晴天','晴天','맑음','ฟ้าใส','Trời quang','Cerah','Despejado','Ciel clair','Klar','Céu limpo','Sereno','Ясно','صافٍ','साफ़ आसमान'],'晴れ はれ 快晴 晴天 sunny clear 맑음 soleado ensoleille sonnig ensolarado sereno ясно'],
['rain','🌧️',['雨','Raining','下雨','下雨','비','ฝนตก','Đang mưa','Hujan','Lloviendo','Pluie','Regen','Chuvendo','Pioggia','Дождь','مطر','बारिश'],'雨 あめ 雨天 rain rainy raining 비 下雨 lluvia pluie regen chuva pioggia дождь'],
['snowing','🌨️',['雪が降っている','Snowing now','正在下雪','正在下雪','눈 오는 중','หิมะตก','Đang có tuyết','Bersalju','Nevando','Il neige','Schneefall','Nevando','Nevica','Идёт снег','ثلج','बर्फ़बारी'],'降雪中 雪が降って 雪降り snowing snowfall 下雪 nevando'],
['hot','🔥',['暑い','Hot','炎热','炎熱','더움','ร้อน','Nóng','Panas','Calor','Chaud','Heiß','Quente','Caldo','Жарко','حار','गर्म'],'暑い あつい 猛暑 hot heat 더위 炎热 calor chaud heiss quente caldo жарко'],
['cold','🥶',['寒い','Cold','寒冷','寒冷','추움','หนาว','Lạnh','Dingin','Frío','Froid','Kalt','Frio','Freddo','Холодно','بارد','ठंडा'],'寒い さむい 極寒 cold freezing 추위 寒冷 frio froid kalt freddo холодно'],
['pop','🔥',['人気','Popular','热门','熱門','인기','ยอดนิยม','Phổ biến','Populer','Popular','Populaire','Beliebt','Popular','Popolare','Популярное','شائع','लोकप्रिय'],'人気 にんき 話題 popular trending top hot 인기 热门 populaire beliebt'],
['hq','🎞️',['高画質','High quality','高画质','高畫質','고화질','คุณภาพสูง','Chất lượng cao','Kualitas tinggi','Alta calidad','Haute qualité','Hohe Qualität','Alta qualidade','Alta qualità','Высокое качество','جودة عالية','उच्च गुणवत्ता'],'高画質 こうがしつ hd fhd full hd 1080p high quality hq 고화질 高清'],
['4k','💎',['4K']*16,'4k uhd 2160p ultra hd 8k 1440p'],
]
def toks(s):return [w for w in s.split() if w]
out={'v':1,'th':{},'kw':[],'cont':{},'ccont':{},'cal':{},'pl':[],'cond':[],'cur':{},'multi':{}}
for th,syn in TH.items():
  names=[I[l]['themes'].get(th,'') for l in L]
  s=set(toks(syn))|{n for n in names if n}
  for n in names:
    for p in n.replace('・',' ').replace('/',' ').split():s.add(p)
  out['th'][th]=sorted(s,key=len,reverse=True)
# multi-word phrases kept as phrases
for th,syn in TH.items():pass
for k,e,th,lab,syn in KW:out['kw'].append({'k':k,'e':e,'th':th,'l':lab,'s':toks(syn)})
for c,(lab,syn) in CONT.items():out['cont'][c]={'l':lab,'s':toks(syn)+[v for v in lab.values()]}
for l in open(os.path.join(D,'countryInfo.txt'),encoding='utf-8'):
  if l.startswith('#'):continue
  x=l.split('\t')
  if len(x)>8 and x[8] in CONT:out['ccont'][x[0]]=x[8]
out['cal']={k:toks(v) for k,v in CAL.items()}
for ja,en,r,b in JR:out['pl'].append({'n':{'ja':ja,'en':en},'s':[ja]+toks(r)+[en.lower()],'b':b,'cc':'JP'})
for ja,r,en,la,lo in PREF:
  km=PREF_KM.get(ja,60)
  if km==0:continue
  suf='都' if ja=='東京' else '道' if ja=='北海道' else '府' if ja in('京都','大阪') else '県'
  out['pl'].append({'n':{'ja':ja+suf,'en':en+' Pref.'},'s':[ja+suf,r+({'都':'と','府':'ふ','県':'けん'}[suf]),en.lower()+(' prefecture'),en.lower()+' ken'],'la':la,'lo':lo,'km':km,'cc':'JP','rd':[ja,r,en.lower()]})
for ja,r,en,la,lo,km in JC+[(ja,r,en,la,lo,30) for ja,r,en,la,lo in [(p[0],p[1],p[2],p[3],p[4]) for p in PREF if p[0] in('東京','大阪','京都','奈良','長崎','熊本','鹿児島','新潟','静岡','福岡','広島','金沢','仙台')]]:
  out['pl'].append({'n':{'ja':ja,'en':en},'s':[ja,r,en.lower()],'la':la,'lo':lo,'km':km,'cc':'JP','rd':[ja,r,en.lower()]})
seen=set()
for w in WC:
  ja,en,r,la,lo=w[:5];km=w[5] if len(w)>5 else 40
  if en in seen:continue
  seen.add(en);out['pl'].append({'n':{'ja':ja,'en':en},'s':[ja,en.lower()]+toks(r),'la':la,'lo':lo,'km':km,'rd':[ja,en.lower()]+toks(r)[:1]})
for k,e,lab,syn in COND:out['cond'].append({'k':k,'e':e,'l':dict(zip(L,lab)),'s':toks(syn)+[x for x in lab]})
# curated cams -> country (nearest gazetteer city) + static viewer counts
cities=[]
for l in open(os.path.join(D,'cities15000.txt'),encoding='utf-8'):
  x=l.split('\t')
  if int(x[14] or 0)>=15000:cities.append((float(x[4]),float(x[5]),x[8]))
import bisect
cities.sort();lats=[c[0] for c in cities]
def near(la,lo):
  i=bisect.bisect_left(lats,la-1.5);j=bisect.bisect_right(lats,la+1.5);best=None
  for a,b,cc in cities[i:j]:
    d=(a-la)**2+((b-lo)*math.cos(math.radians(la)))**2
    if best is None or d<best[0]:best=(d,cc)
  return best[1] if best and best[0]<4 else ''
vw={}
try:
  for k,v in json.load(open(os.path.join(R,'viewers.json'))).items():
    w=(v.get('watching') or [0])[0]
    try:vw[k]=int(str(w).replace(',',''))
    except Exception:pass
except Exception:pass
for f in os.listdir(R):
  if not f.endswith('.json') or f in('live.json','catalog.json','camidx.json','srdict.json') or '.' in f[:-5]:continue
  try:A=json.load(open(os.path.join(R,f)))
  except Exception:continue
  if not isinstance(A,list):continue
  for c in A:
    if not isinstance(c,dict) or 'id' not in c or c.get('lat') is None:continue
    cc=near(c['lat'],c['lon']);out['cur'][c['id']]=[cc,vw.get(c['id'],0)]
json.dump(out,open(os.path.join(R,'srdict.json'),'w'),ensure_ascii=False,separators=(',',':'))
print('srdict',len(out['pl']),'places',len(out['cur']),'curated',os.path.getsize(os.path.join(R,'srdict.json')),'bytes')

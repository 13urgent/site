from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np, json, math, subprocess, wave, textwrap
R=Path('/workspace/13urgent-explication-20261023'); P=R/'production'; O=R/'livraison'; O.mkdir(exist_ok=True)
W,H,FPS=1080,1920,25
RED='#F0263D'; WHITE='#F7F8FC'; MUTED='#AAB3C7'; INK='#171C2A'; LIGHT='#E9EDF4'; GREEN='#12866C'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
fonts={}
def font(n,b=True):
 key=(n,b)
 if key not in fonts:fonts[key]=ImageFont.truetype(BOLD if b else REG,n)
 return fonts[key]
def text(draw,xy,s,size=40,fill=WHITE,b=True):draw.text(xy,s,font=font(size,b),fill=fill,stroke_width=0)
def lines(draw,xy,ss,size=74,fill=WHITE,gap=12):
 x,y=xy
 for s in ss:text(draw,(x,y),s,size,fill);y+=size+gap
 return y
def center(draw,y,s,size=40,fill=WHITE,b=True):
 f=font(size,b);draw.text(((W-draw.textlength(s,font=f))/2,y),s,font=f,fill=fill)
def rr(draw,box,fill,r=32,outline=None,width=1):draw.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=width)
def pill(draw,x,y,s,fill=RED,color=WHITE,size=26):
 width=int(draw.textlength(s,font=font(size)))+40;rr(draw,(x,y,x+width,y+54),fill,27);text(draw,(x+20,y+9),s,size,color);return width
logo=Image.open('/workspace/site/assets/logo-13urgent-web.png').convert('RGBA');logo.thumbnail((320,128))
# Subtle blue/black studio background, a road motif and a red light band.
yy,xx=np.mgrid[0:H,0:W];glow=np.exp(-((xx-900)**2/(650**2)+(yy-670)**2/(900**2)))
a=np.zeros((H,W,3),dtype=np.uint8)
for c,(base,lift) in enumerate([(9,11),(14,13),(25,24)]):a[:,:,c]=base+glow*lift
bg=Image.fromarray(a);d=ImageDraw.Draw(bg)
for y in range(280,1500,90):d.line((65,y,1015,y),fill=(25,33,48),width=1)
d.line((65,1600,1015,1600),fill=(49,59,77),width=2)
bg.paste(logo,(74,120),logo)
text(d,(645,151),'MARSEILLE',27,MUTED);text(d,(645,190),'ET SA RÉGION',27,MUTED)
text(d,(78,1720),'13urgent.fr',36,WHITE);text(d,(78,1770),'Entre professionnels',25,MUTED,False)
text(d,(78,1830),'Une plateforme exploitée par CHRONOSS',21,MUTED,False)
scenes=json.loads((P/'narration.json').read_text());timeline=[];cursor=0
for i,s in enumerate(scenes):
 duration=s['duration']+(.8 if i<6 else 2.2)
 timeline.append(dict(**s,start=cursor,end=cursor+duration,lead=.2));cursor+=duration
D=math.ceil(cursor*FPS)/FPS
# Audio with precise scene offsets and a low original music bed.
sr=22050;full=np.zeros(round(D*sr),dtype=np.float32)
for s in timeline:
 with wave.open(str(P/(s['name']+'.wav')),'rb') as f:samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
 start=round((s['start']+.2)*sr);full[start:start+len(samples)]+=samples
with wave.open(str(P/'narration-complete.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(full,-1,1)*32767).astype('<i2').tobytes())
# Caption phrases follow each spoken sentence, also provided as an independent SRT.
captions=[]
for s in timeline:
 words=s['text'].split();parts=[];chunk=[]
 for word in words:
  chunk.append(word)
  if len(' '.join(chunk))>=62 or (word.endswith(('.', '?', ':')) and len(chunk)>=4):parts.append(' '.join(chunk));chunk=[]
 if chunk:parts.append(' '.join(chunk))
 total=sum(len(t) for t in parts);at=s['start']+.2
 for part in parts:
  dur=s['duration']*len(part)/total;captions.append((at,at+dur,part));at+=dur

def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(O/'13urgent-explication.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n'+ '\n'.join(textwrap.wrap(t,38)) for i,(a,b,t) in enumerate(captions))+'\n')
(P/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2))

def base(step,head,sub):
 im=Image.new('RGBA',(W,H));dr=ImageDraw.Draw(im)
 pill(dr,80,310,step,fill='#283145',size=27)
 size=76
 while max(dr.textlength(t,font=font(size)) for t in head)>930:size-=1
 lines(dr,(76,402),head,size)
 lines(dr,(80,605),sub,32,fill=MUTED,gap=14)
 return im,dr

def field(dr,y,label,value):
 text(dr,(125,y),label,25,'#616D82');rr(dr,(125,y+42,955,y+124),'#F0F3F8',18);text(dr,(149,y+62),value,34,INK)
def checklist(dr,y,n,title,subtitle):
 dr.ellipse((124,y+4,185,y+65),fill=RED);text(dr,(143,y+8),str(n),34)
 text(dr,(211,y),title,35,INK);text(dr,(211,y+52),subtitle,26,'#616D82',False)

layers=[]
for i,s in enumerate(scenes):
 if i==0:
  im,dr=base('TRANSPORT EXPRESS',['UN TRANSPORT','URGENT ?'],['Une demande. Des propositions.','Votre choix.'])
  rr(dr,(80,800,1000,1430),'#182233',42,outline='#354157',width=2)
  pill(dr,120,845,'COLIS · PALETTES · LOTS',fill='#29364D',size=25)
  text(dr,(130,978),'Marseille',54);text(dr,(130,1175),'Votre destination',45)
  dr.line((160,1070,900,1070),fill='#4B5970',width=10)
  dr.ellipse((140,1050,180,1090),fill=RED);dr.ellipse((880,1050,920,1090),fill=WHITE)
  text(dr,(130,1330),'Trouvez votre solution professionnelle.',29,MUTED,False)
 elif i==1:
  im,dr=base('ÉTAPE 1 · DONNEUR D’ORDRE',['DÉPOSEZ','VOTRE DEMANDE.'],['Compte professionnel requis.','Publication gratuite.'])
  rr(dr,(80,790,1000,1435),WHITE,38)
  text(dr,(125,830),'Nouvelle demande',40,INK)
  field(dr,910,'TRAJET','Marseille → Aubagne')
  field(dr,1100,'DATE ET VÉHICULE','Selon votre besoin · Fourgon')
  rr(dr,(125,1300,955,1390),RED,20);text(dr,(245,1323),'Créer la demande →',34)
 elif i==2:
  im,dr=base('ÉTAPE 2 · VOUS CHOISISSEZ',['COMPAREZ LES','PROPOSITIONS.'],['Des tarifs confidentiels.','Vous choisissez votre transporteur.'])
  for n,y in enumerate([800,1025]):
   rr(dr,(80,y,1000,y+190),WHITE,30,outline=RED if n==1 else None,width=4)
   text(dr,(125,y+30),'Proposition '+('A' if n==0 else 'B'),36,INK)
   text(dr,(125,y+95),'Tarif HT · Transporteur professionnel',28,'#616D82',False)
   pill(dr,780,y+33,'PRIVÉ',fill='#E8EEF4',color=INK,size=22)
  rr(dr,(80,1265,1000,1420),RED,30);text(dr,(125,1305),'Choisir une proposition →',39)
 elif i==3:
  im,dr=base('ÉTAPE 3 · VOTRE ESPACE',['SUIVEZ','VOTRE COURSE.'],['Des étapes déclarées par les parties.','La réalisation est confirmée par le client.'])
  rr(dr,(80,790,1000,1450),WHITE,36)
  for n,(label,small) in enumerate([('Course attribuée','Transporteur sélectionné'),('En route vers l’enlèvement','Étape déclarée'),('Marchandise chargée','Étape déclarée'),('Livraison déclarée','Confirmation client attendue')]):
   y=845+n*145
   if n<3:dr.line((151,y+25,151,y+168),fill='#D8DFE9',width=6)
   dr.ellipse((126,y,176,y+50),fill=GREEN if n<3 else RED)
   text(dr,(210,y-5),label,34,INK);text(dr,(210,y+49),small,27,'#616D82',False)
 elif i==4:
  im,dr=base('TARIFICATION · DONNEUR D’ORDRE',['DES FRAIS','CLAIREMENT ANNONCÉS.'],['Lors d’une attribution commerciale confirmée.'])
  rr(dr,(80,800,1000,1430),WHITE,38)
  text(dr,(150,838),'1,5 %',156,RED);text(dr,(680,938),'HT',55,INK)
  lines(dr,(130,1050),['du prix HT du transport','+ TVA applicable'],37,INK,gap=20)
  dr.line((130,1185,950,1185),fill='#D7DDE8',width=2)
  lines(dr,(130,1220),['Exemple : 300 € HT de transport','→ 4,50 € HT de frais, TVA en sus'],29,INK,gap=18)
  text(dr,(130,1350),'Facturation mensuelle CHRONOSS.',29,'#616D82',False)
 elif i==5:
  im,dr=base('VOUS ÊTES TRANSPORTEUR ?',['PROPOSEZ','VOTRE TARIF.'],['Vos concurrents ne voient pas vos prix.'])
  rr(dr,(80,790,1000,1435),WHITE,36)
  checklist(dr,850,1,'Choisissez votre forfait','Selon vos besoins professionnels.')
  checklist(dr,1025,2,'Transmettez vos documents','Autorisations et assurances valides.')
  checklist(dr,1200,3,'Dossier et droits validés','Vous pouvez proposer votre tarif.')
  text(dr,(125,1370),'Conditions et forfaits sur 13urgent.fr',27,'#616D82',False)
 else:
  im=Image.new('RGBA',(W,H));dr=ImageDraw.Draw(im)
  big=Image.open('/workspace/site/assets/logo-13urgent-web.png').convert('RGBA');big.thumbnail((900,360));im.paste(big,((W-big.width)//2,365),big)
  center(dr,780,'VOTRE URGENCE.',67);center(dr,875,'NOTRE PRIORITÉ.',67,RED)
  rr(dr,(80,1055,1000,1195),RED,30);center(dr,1080,'13urgent.fr',82)
  center(dr,1255,'Une question ? Contactez-nous.',35)
  center(dr,1320,'contact@13urgent.fr',34,MUTED,False)
  center(dr,1380,'04 91 82 63 12',40)
 layers.append(im)
 # Storyboard image, useful for visual verification.
 preview=bg.convert('RGBA');preview.alpha_composite(im);preview.convert('RGB').save(P/f'scene-{i}.jpg',quality=92)

# Render with gentle entrances, route movement, progress bar and burned-in captions.
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(P/'video-sans-son.mp4')]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for frame in range(round(D*FPS)):
 t=frame/FPS;idx=next((i for i,s in enumerate(timeline) if t<s['end']),6);s=timeline[idx];local=t-s['start'];entrance=min(1,local/.35);ease=1-(1-entrance)**3
 img=bg.copy().convert('RGBA');layer=layers[idx]
 if entrance<1:
  shifted=Image.new('RGBA',(W,H));shifted.paste(layer,(0,round(60*(1-ease))));layer=shifted;layer.putalpha(layer.getchannel('A').point(lambda a:int(a*ease)))
 img.alpha_composite(layer);dr=ImageDraw.Draw(img)
 if idx==0:
  x=160+740*min(1,max(0,(local-.4)/(s['duration']-.4)))
  # A compact delivery vehicle travels along the illustrative route.
  rr(dr,(x-57,1034,x+35,1066),RED,7);dr.polygon([(x+35,1044),(x+58,1044),(x+70,1066),(x+35,1066)],fill=WHITE)
  dr.ellipse((x-40,1057,x-21,1076),fill='#0C1322');dr.ellipse((x+38,1057,x+57,1076),fill='#0C1322')
 if idx in [0,1,2,3]:text(dr,(82,1470),'ILLUSTRATION · DONNÉES FICTIVES',21,MUTED,False)
 # Captions keep a large bottom margin for social platform controls.
 cap=next((c for a,b,c in captions if a<=t<b),None)
 if cap:
  parts=textwrap.wrap(cap,41);height=35*len(parts)+32;top=1568-height
  rr(dr,(70,top,1010,1570),'#080D17',20)
  for k,line in enumerate(parts):center(dr,top+12+k*35,line,29,WHITE,False)
 rr(dr,(80,1653,1000,1661),'#2F394B',4);rr(dr,(80,1653,80+max(8,920*t/D),1661),RED,4)
 proc.stdin.write(img.convert('RGB').tobytes())
 if frame%250==0:print(f'Rendu {frame}/{round(D*FPS)}',flush=True)
proc.stdin.close();assert proc.wait()==0
music='/workspace/13urgent-videos-commerciales-20261020/production/musique-pop-lumineuse.wav'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(P/'video-sans-son.mp4'),'-i',str(P/'narration-complete.wav'),'-stream_loop','-1','-i',music,'-filter_complex',f'[1:a]aresample=48000,loudnorm=I=-16:TP=-2:LRA=7[v];[2:a]volume=0.085,atrim=duration={D},afade=t=in:d=0.3,afade=t=out:st={D-1.5}:d=1.5[m];[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9:level=0[a]','-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t',str(D),'-movflags','+faststart',str(O/'13urgent-explication-reseaux.mp4')],check=True)
# Cover and a contact sheet.
cover=bg.convert('RGBA');cover.alpha_composite(layers[0]);cover.convert('RGB').save(O/'13urgent-explication-couverture.jpg',quality=94)
thumb=Image.new('RGB',(1080,960),'#080C14')
for i in range(6):
 im=Image.open(P/f'scene-{i}.jpg');im.thumbnail((360,480));thumb.paste(im,((i%3)*360,(i//3)*480))
thumb.save(P/'storyboard.jpg',quality=93)
(O/'CREDITS.txt').write_text('13 URGENT — Vidéo explicative, 23 octobre 2026.\nVisuels et animation créés pour CHRONOSS. Exemples fictifs.\nLogo fourni par CHRONOSS. Musique originale synthétisée pour ce projet.\nVoix de synthèse : Piper / SIWIS fr_FR medium, exécutée localement via sherpa-onnx.\nSource modèle : https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models\nCorpus SIWIS : https://datashare.is.ed.ac.uk/handle/10283/2353 — CC BY 4.0.\nLicence : https://creativecommons.org/licenses/by/4.0/\nAucun client réel montré. Suivi déclaratif, sans géolocalisation.\n')
print('TERMINE',D,str(O/'13urgent-explication-reseaux.mp4'),flush=True)

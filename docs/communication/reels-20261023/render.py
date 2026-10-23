from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import subprocess,math,wave,json,textwrap,hashlib,shutil
import numpy as np
import argparse
parser=argparse.ArgumentParser()
parser.add_argument("--root",default="/workspace/13urgent-social-20261023")
args=parser.parse_args()
R=Path(args.root).resolve();R.mkdir(parents=True,exist_ok=True);P=R/'production';O=R/'livraison';P.mkdir(exist_ok=True);O.mkdir(exist_ok=True)
SOURCE=P/'source-explication.mp4'
SRT=P/'source-explication.srt'
W,H,FPS=1080,1920,25
RED='#F0263D';WHITE='#F6F7FB';MUTED='#ABB5C7';INK='#151B29';GREEN='#16846C'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n,b=True):return ImageFont.truetype(BOLD if b else REG,n)
def text(d,xy,s,size=42,color=WHITE,b=True):
 assert d.textlength(s,font=font(size,b))<=900,(s,size)
 d.text(xy,s,font=font(size,b),fill=color)
def center(d,y,s,size=42,color=WHITE,b=True):
 f=font(size,b);d.text(((W-d.textlength(s,font=f))/2,y),s,font=f,fill=color)
def box(d,xy,fill,r=28,outline=None,width=2):d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=width)
def base(tag,heads,sub):
 im=Image.new('RGB',(W,H),'#0B1020');d=ImageDraw.Draw(im)
 for y in range(0,H,3):d.line((0,y,W,y),fill=(11+int(6*y/H),16+int(4*y/H),32+int(6*y/H)),width=3)
 d.line((75,285,950,285),fill='#2D3547',width=2)
 logo=Image.open('/workspace/site/assets/logo-13urgent-web.png').convert('RGBA');logo.thumbnail((350,145));im.paste(logo,(75,125),logo)
 text(d,(620,160),'MARSEILLE',27,MUTED);text(d,(620,202),'ET SA RÉGION',25,MUTED)
 text(d,(80,330),tag,25,RED)
 size=76
 while max(d.textlength(s,font=font(size)) for s in heads)>900:size-=1
 for i,s in enumerate(heads):text(d,(75,408+i*89),s,size)
 for i,s in enumerate(sub):text(d,(80,625+i*48),s,32,MUTED,False)
 text(d,(80,1600),'13urgent.fr',37);text(d,(80,1653),'Exploité par CHRONOSS · Entre professionnels',23,MUTED,False)
 return im,d

def route(d):
 box(d,(80,805,950,1290),'#182236',36,outline='#34405A')
 text(d,(125,852),'COLIS · PALETTES · LOTS',29,MUTED)
 text(d,(125,950),'Marseille',55);text(d,(125,1167),'Votre destination',40)
 d.line((155,1074,870,1074),fill='#69748A',width=8)
 for x,c in [(155,RED),(870,WHITE)]:d.ellipse((x-17,1057,x+17,1091),fill=c)
 box(d,(470,1032,570,1067),RED,7);d.polygon([(570,1042),(596,1042),(611,1067),(570,1067)],fill=WHITE)
 for x in [490,586]:d.ellipse((x,1056,x+19,1076),fill='#080D18')
 text(d,(110,1345),'Illustration · trajet fictif',25,MUTED,False)

scenes={}
im,d=base('DONNEURS D’ORDRE',['UN TRANSPORT','URGENT ?'],['Une palette ? Un colis ?','Préparez votre demande en ligne.']);route(d);scenes['urgence']=im
im,d=base('PUBLICATION GRATUITE',['DÉPOSEZ','VOTRE DEMANDE.'],['Créez votre compte professionnel.'])
screen=Image.open(P/'formulaire-exemple.png').convert('RGB');screen.thumbnail((870,770));box(d,(80,770,950,770+screen.height+24),WHITE,30);im.paste(screen,((W-screen.width)//2,782));text(d,(105,1405),'Capture du formulaire · exemple fictif',24,MUTED,False);scenes['demande']=im
im,d=base('VOUS CHOISISSEZ',['COMPAREZ LES','PROPOSITIONS.'],['Votre choix, selon votre besoin.'])
for n,y in enumerate([810,1030]):
 box(d,(80,y,950,y+175),WHITE,26,outline=RED if n==1 else None,width=4)
 text(d,(120,y+28),'Proposition '+chr(65+n),38,INK);text(d,(120,y+95),'Tarif HT · transporteur professionnel',28,'#616D82',False)
text(d,(100,1260),'Les autres transporteurs ne voient',31,MUTED,False);text(d,(100,1310),'pas les prix de leurs concurrents.',31,MUTED,False);text(d,(100,1380),'Illustration · propositions fictives',24,MUTED,False);scenes['compare']=im
im,d=base('DES FRAIS ANNONCÉS AVANT CONFIRMATION',['LE DÉPÔT','EST GRATUIT.'],['Lors de l’attribution commerciale confirmée :'])
box(d,(80,800,950,1375),WHITE,36);text(d,(125,835),'1,5 %',150,RED);text(d,(745,940),'HT',48,INK)
text(d,(125,1055),'du prix HT du transport',43,INK);text(d,(125,1125),'+ TVA applicable',39,INK)
d.line((125,1210,910,1210),fill='#D9DFE8',width=2);text(d,(125,1250),'Facturation mensuelle CHRONOSS',30,'#616D82',False);scenes['frais']=im
im,d=base('DONNEURS D’ORDRE PROFESSIONNELS',['VOTRE PROCHAINE','DEMANDE COMMENCE ICI.'],['Marseille et sa région.'])
box(d,(80,850,950,1000),RED,30);center(d,880,'13urgent.fr',82)
center(d,1110,'INSCRIVEZ VOTRE ENTREPRISE',38);center(d,1190,'Publication d’une demande gratuite',32,MUTED,False);center(d,1280,'Frais à l’attribution selon conditions',29,MUTED,False);scenes['cta-donneur']=im
im,d=base('TRANSPORTEURS PROFESSIONNELS',['VOUS ROULEZ','DANS LA RÉGION ?'],['Découvrez 13 URGENT.'])
route(d);scenes['transporteur']=im
im,d=base('AVANT DE PROPOSER VOTRE TARIF',['UN DOSSIER','À FAIRE VALIDER.'],['Autorisations et assurances valides.'])
for n,(title,sub) in enumerate([('Entreprise vérifiée','SIRET et qualité professionnelle'),('Documents contrôlés','Autorisations et assurances'),('Droits d’accès actifs','Selon votre forfait et votre dossier')]):
 y=815+n*185;box(d,(80,y,950,y+155),WHITE,25);d.ellipse((115,y+42,175,y+102),fill=RED);text(d,(133,y+49),str(n+1),30);text(d,(205,y+26),title,37,INK);text(d,(205,y+86),sub,28,'#616D82',False)
scenes['dossier']=im
im,d=base('PROPOSITIONS CONFIDENTIELLES',['VOTRE PRIX.','VOTRE PROPOSITION.'],['Vos concurrents ne voient pas votre tarif.'])
box(d,(80,830,950,1270),WHITE,36);text(d,(130,890),'Proposer un tarif HT',44,INK);box(d,(130,1010,900,1120),'#EEF1F6',20);text(d,(155,1043),'Votre montant en euros',31,'#616D82',False);text(d,(130,1170),'Accès soumis aux droits et au dossier.',29,INK,False);text(d,(100,1340),'Illustration · aucune offre réelle',25,MUTED,False);scenes['confidentiel']=im
im,d=base('FORFAITS SUR LE SITE',['CHOISISSEZ','VOTRE FORFAIT.'],['Selon vos besoins et vos droits d’accès.'])
box(d,(80,815,950,1355),WHITE,36)
for n,s in enumerate(['Consultez les conditions et les quotas.','Faites vérifier votre dossier.','Pour un forfait payant : virement,','puis activation après rapprochement.']):text(d,(125,865+n*108),s,31,INK,n<2)
scenes['forfait']=im
im,d=base('TRANSPORTEURS PROFESSIONNELS',['REJOIGNEZ','13 URGENT.'],['Marseille et sa région.'])
box(d,(80,850,950,1000),RED,30);center(d,880,'13urgent.fr',82)
center(d,1110,'INSCRIVEZ VOTRE ENTREPRISE',38);center(d,1200,'Dossier et droits à valider',35,MUTED,False);center(d,1290,'Aucune course ni aucun revenu garanti',27,MUTED,False);scenes['cta-transporteur']=im
for name,im in scenes.items():im.save(P/(name+'.png'))

# Captions de la narration française existante, remontées sans nouveau texte parlé.
def seconds(t):
 h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
captions=[]
for block in SRT.read_text().strip().split('\n\n'):
 rows=block.splitlines();a,b=rows[1].split(' --> ');captions.append((seconds(a),seconds(b),' '.join(rows[2:])))
def stamp(t,ass=False):
 if ass:return f'{int(t)//3600}:{int(t)//60%60:02}:{t%60:05.2f}'
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
tracks={
 'donneurs-ordre':[('urgence',0,3.60),('demande',3.993,5.12),('compare',9.512,4.52),('frais',18.572,6.12),('cta-donneur',32.898,5.64)],
 'transporteurs':[('transporteur',25.068,3.64),('dossier',28.708,3.80),('confidentiel',None,4.00),('forfait',None,4.92),('cta-transporteur',32.898,5.64)]
}
# Musique instrumentale originale : rythme léger, sans morceau tiers.
sr=48000;duration=25;t=np.arange(sr*duration)/sr;music=np.zeros_like(t)
for j in range(math.ceil(duration/2)):
 chord=[(220,277.18,329.63),(174.61,220,261.63),(196,246.94,293.66),(164.81,207.65,246.94)][j%4]
 mask=(t>=j*2)&(t<(j+1)*2);local=t[mask]-j*2;env=np.sin(np.pi*local/2)**2
 for f in chord:music[mask]+=.012*np.sin(2*np.pi*f*local)*env
for at in np.arange(0,duration,.5):
 k=int(at*sr);n=min(int(.18*sr),len(t)-k);tt=np.arange(n)/sr;music[k:k+n]+=.025*np.sin(2*np.pi*(80*tt-90*tt*tt))*np.exp(-tt*22)
with wave.open(str(P/'musique-originale.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((music*32767).astype('<i2').tobytes())
for name,sequence in tracks.items():
 output_caps=[];cursor=0;clips=[];filters=[];audios=[]
 voiced=[s for s in sequence if s[1] is not None];filters.append(f'[0:a]asplit={len(voiced)}'+''.join(f'[v{i}]' for i in range(len(voiced)))+';');voice_n=0
 for i,(scene,start,dur) in enumerate(sequence):
  frames=round(dur*FPS);assert abs(frames/FPS-dur)<.001
  clip=P/f'{name}-{i}.mp4';clips.append(clip)
  vf=f"zoompan=z='min(zoom+0.00012,1.012)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.10,fade=t=out:st={dur-.10}:d=0.10"
  subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(P/(scene+'.png')),'-vf',vf,'-t',str(dur),'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',str(clip)],check=True)
  if start is not None:
   filters.append(f'[v{voice_n}]atrim=start={start}:duration={dur},asetpts=PTS-STARTPTS,afade=t=in:d=0.035,afade=t=out:st={dur-.05}:d=0.05[a{i}];');voice_n+=1
   for a,b,s in captions:
    if min(b,start+dur)>max(a,start):output_caps.append((cursor+max(a,start)-start,cursor+min(b,start+dur)-start,s))
  else:filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={dur}[a{i}];')
  audios.append(f'[a{i}]');cursor+=dur
  print(name,scene,'rendu',flush=True)
 ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Caption,DejaVu Sans,36,&H00FFFFFF,&H000000FF,&H00100D08,&H990D0A05,0,0,0,0,100,100,0,0,3,2,0,2,90,140,350,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
 for a,b,s in output_caps:ass+=f'Dialogue: 0,{stamp(a,True)},{stamp(b,True)},Caption,,0,0,0,,'+'\\N'.join(textwrap.wrap(s,40))+'\n'
 (P/(name+'.ass')).write_text(ass)
 (O/(name+'.srt')).write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n'+'\n'.join(textwrap.wrap(s,40)) for i,(a,b,s) in enumerate(output_caps))+'\n')
 (P/(name+'-clips.txt')).write_text(''.join("file '"+str(c)+"'\n" for c in clips))
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(P/(name+'-clips.txt')),'-c','copy',str(P/(name+'-sans-son.mp4'))],check=True)
 filters.append(''.join(audios)+f'concat=n={len(sequence)}:v=0:a=1[voice];[1:a]atrim=duration={cursor},volume=0.5,afade=t=in:d=0.3,afade=t=out:st={cursor-1}:d=1[music];[voice][music]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-2:LRA=7[out]')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(SOURCE),'-i',str(P/'musique-originale.wav'),'-filter_complex',''.join(filters),'-map','[out]','-t',str(cursor),'-c:a','pcm_s16le','-ar','48000',str(P/(name+'-audio.wav'))],check=True)
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(P/(name+'-sans-son.mp4')),'-i',str(P/(name+'-audio.wav')),'-vf',f"ass={P/(name+'.ass')}",'-map','0:v:0','-map','1:a:0','-r','30','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',str(cursor),'-movflags','+faststart',str(O/(name+'.mp4'))],check=True)
 scenes[sequence[0][0]].save(O/(name+'-couverture.jpg'),quality=95)
 (P/(name+'-timeline.json')).write_text(json.dumps(sequence,ensure_ascii=False,indent=2))
 print('TERMINE',name,cursor,flush=True)
# Planche de contrôle des dix scènes.
board=Image.new('RGB',(1080,768),'#0B1020')
for i,scene in enumerate([a for seq in tracks.values() for a,_,_ in seq]):
 im=scenes[scene].copy();im.thumbnail((216,384));board.paste(im,((i%5)*216,(i//5)*384))
board.save(P/'storyboard.jpg',quality=95)
(O/'CREDITS.txt').write_text('13 URGENT / CHRONOSS — Kit TikTok et Instagram, 23 octobre 2026.\nLogo fourni par CHRONOSS. Graphismes et musique instrumentale originaux créés pour le projet.\nCapture du formulaire du site : données fictives, présentation recadrée, aucune demande envoyée.\nVoix française synthétique réutilisée avec un nouveau montage depuis la vidéo explicative du projet.\nPiper/SIWIS fr_FR medium ; corpus SIWIS CC BY 4.0 : https://datashare.is.ed.ac.uk/handle/10283/2353 ; https://creativecommons.org/licenses/by/4.0/\nSource modèle : https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models\nSource vidéo : https://13urgent.fr/videos/explication/13urgent-explication-reseaux.mp4\nEmpreinte source SHA256 : '+hashlib.sha256(SOURCE.read_bytes()).hexdigest()+'\nAucun compte réel, aucune offre réelle, aucune promesse de disponibilité ou de revenu.\n')

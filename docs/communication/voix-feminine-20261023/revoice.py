from pathlib import Path
import subprocess,json,textwrap,wave
import numpy as np
R=Path('/workspace/13urgent-social-voix-naturelle-20261023');P=R/'production';O=R/'livraison'
BASE=Path('/workspace/13urgent-social-20261023/production');SR=48000;D=25
scenes=json.loads((P/'narration.json').read_text());durations=[3.60,5.12,4.52,6.12,5.64]
full=np.zeros(SR*D,dtype=np.float32);captions=[];timeline=[];cursor=0
for scene,duration in zip(scenes,durations):
 name=scene['name'];wav=P/(name+'.wav')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(P/(name+'.mp3')),'-ac','1','-ar',str(SR),'-c:a','pcm_s16le',str(wav)],check=True)
 with wave.open(str(wav),'rb') as w:samples=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
 lead=.12;assert len(samples)/SR+lead<duration
 start=round((cursor+lead)*SR);full[start:start+len(samples)]+=samples
 words=[json.loads(line) for line in (P/(name+'-timings.jsonl')).read_text().splitlines() if line.strip()]
 words=[w for w in words if w['type']=='WordBoundary']
 chunks=[];chunk=[]
 for word in words:
  if chunk and len(' '.join(w['text'] for w in chunk+[word]))>52:chunks.append(chunk);chunk=[]
  chunk.append(word)
 if chunk:chunks.append(chunk)
 for chunk in chunks:
  a=cursor+lead+chunk[0]['offset']/1e7;b=cursor+lead+(chunk[-1]['offset']+chunk[-1]['duration'])/1e7
  text=' '.join(w['text'] for w in chunk)
  text=text.replace('confirmée un virgule cinq pour cent','confirmée : 1,5 %').replace('hors taxes','HT').replace('plus TVA','TVA en sus').replace('treize urgent point F R','13urgent.fr').replace('Treize Urgent','13 URGENT')
  # Les sous-titres gardent une transcription fidèle ; le chiffre est aussi affiché en grand.
  captions.append((a,min(cursor+duration,b+.10),text))
 timeline.append(dict(**scene,start=cursor,end=cursor+duration,lead=lead))
 cursor+=duration
assert abs(cursor-D)<.001
with wave.open(str(P/'narration-feminine.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((np.clip(full,-1,1)*32767).astype('<i2').tobytes())
def stamp(t,ass=False):
 if ass:return f'{int(t)//3600}:{int(t)//60%60:02}:{t%60:05.2f}'
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
srt='\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n'+'\n'.join(textwrap.wrap(s,40)) for i,(a,b,s) in enumerate(captions))+'\n'
(O/'donneurs-ordre-voix-feminine.srt').write_text(srt)
(O/'donneurs-ordre-voix-feminine.vtt').write_text('WEBVTT\n\n'+'\n'.join(line.replace(',','.') if ' --> ' in line else line for line in srt.splitlines() if not line.isdigit()))
ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Caption,DejaVu Sans,36,&H00FFFFFF,&H000000FF,&H00100D08,&H990D0A05,0,0,0,0,100,100,0,0,3,2,0,2,90,140,350,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
for a,b,s in captions:ass+=f'Dialogue: 0,{stamp(a,True)},{stamp(b,True)},Caption,,0,0,0,,'+'\\N'.join(textwrap.wrap(s,40))+'\n'
(P/'sous-titres.ass').write_text(ass)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(P/'narration-feminine.wav'),'-af','loudnorm=I=-16:TP=-2:LRA=7','-c:a','libmp3lame','-b:a','192k',str(O/'narration-feminine.mp3')],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(BASE/'donneurs-ordre-sans-son.mp4'),'-i',str(P/'narration-feminine.wav'),'-i',str(BASE/'musique-originale.wav'),'-filter_complex',f'[1:a]loudnorm=I=-16:TP=-2:LRA=7[v];[2:a]volume=0.45,afade=t=in:d=0.4,afade=t=out:st=23.5:d=1.5[m];[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.85:level=0[a]','-vf',f'ass={P/"sous-titres.ass"}','-map','0:v:0','-map','[a]','-r','30','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-t',str(D),'-movflags','+faststart',str(O/'donneurs-ordre-voix-feminine.mp4')],check=True)
(P/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2))
(O/'CREDITS.txt').write_text('13 URGENT / CHRONOSS — Nouvelle narration féminine, 23 octobre 2026.\nLogo CHRONOSS, graphismes et musique instrumentale originaux du projet.\nCapture du formulaire avec données fictives, aucune demande envoyée.\nNarration française synthétique : Microsoft fr-FR-VivienneMultilingualNeural, produite avec edge-tts 7.3.1. Rythme -3 %, hauteur -1 Hz ; aucune accélération de l’audio au montage. Aucun clonage d’une personne réelle.\nLe montage précédent utilisait Piper/SIWIS ; cet ancien enregistrement n’est pas utilisé dans cette version.\nInformations commerciales inchangées : publication gratuite ; frais à l’attribution commerciale confirmée de 1,5 % du prix HT du transport, TVA applicable en sus ; facturation mensuelle CHRONOSS.\n')
print('TERMINE vidéo féminine 25 secondes et narration seule',flush=True)

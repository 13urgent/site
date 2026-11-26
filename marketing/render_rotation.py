#!/usr/bin/env python3
"""Render a factual social capsule from an approved voiced master + original music.

Pillow + FFmpeg only. Voice content/tempo remain those of the approved source;
music is low and ducked by speech. No external paid generation or trend claim.
"""
from __future__ import annotations
import argparse,array,hashlib,json,math,os,re,shutil,subprocess
from datetime import date
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
SOURCES={
'urgent':{'local':'/workspace/site/videos/linkedin-20261031/13urgent-linkedin-avec-voix.mp4','url':'https://raw.githubusercontent.com/13urgent/site/gh-pages/videos/linkedin-20261031/13urgent-linkedin-avec-voix.mp4'},
'mon_exploit':{'local':'/workspace/montage-20s-20261123/13URGENT-MONEXPLOIT-VOIX-CORRIGEE.mp4','url':'https://raw.githubusercontent.com/13urgent/site/gh-pages/videos/monexploit-20261123/13urgent-monexploit-voix-corrigee-20s.mp4'},
'chronoss':{'local':'/workspace/site/videos/particuliers-20261102/13urgent-particuliers-avec-voix.mp4','url':'https://raw.githubusercontent.com/13urgent/site/gh-pages/videos/particuliers-20261102/13urgent-particuliers-avec-voix.mp4'},
}
MUSIC_LOCAL=Path('/workspace/13urgent-activation-marketing-20261106/video/example/musique-originale.wav')
MUSIC_URL='https://raw.githubusercontent.com/13urgent/site/gh-pages/videos/rotation-20261127/original-background.wav'
PALETTES=[('#0c1825','#172c3d','#ed263d','#ffffff','#c1d1dd'),('#f3f0e9','#ffffff','#c51b32','#132c3e','#405a69'),('#102d32','#1b4245','#f4c45c','#ffffff','#c0d9d8'),('#202139','#323450','#f6788b','#ffffff','#cdd0eb')]

def fonts():
    for path in [Path(os.environ.get('MARKETING_FONT_DIR','')),ROOT.parent/'video/assets/fonts',Path('/usr/share/fonts/truetype/dejavu')]:
        if (path/'DejaVuSans-Bold.ttf').exists():return path
    raise RuntimeError('font_unavailable')

def font(size,bold=True):return ImageFont.truetype(str(fonts()/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)

def wrapped(draw,value,size,width,bold=True):
    lines=[];current=''
    for word in value.split():
        proposed=(current+' '+word).strip()
        if current and draw.textlength(proposed,font=font(size,bold))>width:lines.append(current);current=word
        else:current=proposed
    if current:lines.append(current)
    return lines

def fetch(url,path):
    if path.exists() and path.stat().st_size:return path
    path.parent.mkdir(parents=True,exist_ok=True)
    with urlopen(Request(url,headers={'User-Agent':'13URGENT-rotation/2.0'}),timeout=45) as response:
        if response.status!=200:raise RuntimeError('media_download_failed')
        temporary=path.with_suffix(path.suffix+'.part')
        with temporary.open('wb') as stream:shutil.copyfileobj(response,stream)
    temporary.replace(path);return path

def source_for(service,cache):
    source=SOURCES[service];local=Path(source['local'])
    return local if local.exists() else fetch(source['url'],cache/(service+'.mp4'))

def audio_metrics(video):
    result=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True)
    mean=re.search(r'mean_volume:\s*(-?[0-9.]+) dB',result.stderr);peak=re.search(r'max_volume:\s*(-?[0-9.]+) dB',result.stderr)
    if not mean or not peak:raise RuntimeError('audio_measurement_failed')
    return {'mean_db':float(mean.group(1)),'peak_db':float(peak.group(1))}

def probe(video):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))


def voice_correlation(source,mixed):
    """Verify the approved speech signal survives; music-only cannot pass.

    Allow a small codec/limiter delay, independently of absolute loudness.
    This is signal verification, not an invented speech transcription.
    """
    def pcm(path):
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','8000','-f','f32le','-'])
        values=array.array('f');values.frombytes(raw)
        if __import__('sys').byteorder!='little':values.byteswap()
        return list(values)[::4]
    original,result=pcm(source),pcm(mixed)
    # Search ±10ms at the decimated 2kHz sample rate.
    best=0.0
    for lag in range(-20,21):
        a=max(0,-lag);b=max(0,lag);length=min(len(original)-a,len(result)-b)
        if length<100:continue
        xx=yy=xy=0.0
        for i in range(length):
            x,y=original[a+i],result[b+i];xx+=x*x;yy+=y*y;xy+=x*y
        if xx and yy:best=max(best,xy/math.sqrt(xx*yy))
    return round(best,5)


def business_panel(topic,pane,palette,phase,path):
    """A plainly labelled diagram, never a fabricated client/application screen."""
    bg,panel,accent,white,muted=palette
    im=Image.new('RGBA',(720,1280),(0,0,0,0));d=ImageDraw.Draw(im)
    x1,y1,x2,y2=pane;d.rounded_rectangle((x1+5,y1+5,x2-5,y2-5),radius=20,fill=panel,outline=accent,width=3)
    d.text((x1+22,y1+24),'ILLUSTRATION DU PARCOURS',font=font(16),fill=muted)
    title=topic['hook'] if phase==0 else 'LES INFORMATIONS UTILES'
    for j,line in enumerate(wrapped(d,title,29,x2-x1-46)):d.text((x1+22,y1+65+j*36),line,font=font(29),fill=white)
    words=topic['hook'].lower()
    y=y1+213
    kind=('photo' if 'photo' in words else
          'vehicle' if any(w in words for w in ['défaut','véhicule','signalement']) else
          'chat' if any(w in words for w in ['message','consigne','échange']) else
          'document' if any(w in words for w in ['document','pdf','signature','ecmr','ecmr','lettre','confirmation']) else
          'calendar' if any(w in words for w in ['planning','date','calendrier','affect','tournée']) else
          'stairs' if any(w in words for w in ['étage','escalier','ascenseur','accès']) else
          'offers' if any(w in words for w in ['offre','choisir','proposition']) and topic['service']=='urgent' else
          'boxes' if any(w in words for w in ['palette','poids','volume','meuble','colis','dimensions','canapé']) else 'route')
    if phase==1:kind='steps'
    if kind=='photo':
        d.rounded_rectangle((169,y+10,548,y+172),radius=19,fill=bg,outline=accent,width=4)
        d.rounded_rectangle((217,y-14,321,y+23),radius=8,fill=accent)
        d.ellipse((298,y+37,419,y+153),outline=white,width=7)
        d.ellipse((331,y+70,386,y+121),outline=accent,width=5)
    elif kind=='vehicle':
        d.rounded_rectangle((162,y+57,420,y+153),radius=9,fill=accent)
        d.rectangle((420,y+88,477,y+153),fill=white)
        for x in [215,443]:d.ellipse((x-20,y+134,x+20,y+174),fill=bg,outline=muted,width=5)
        d.polygon([(528,y-12),(592,y+99),(464,y+99)],fill='#f4c45c')
        d.text((518,y+15),'!',font=font(48),fill='#102d32')
    elif kind=='document':
        d.rounded_rectangle((255,y-25,464,y+190),radius=14,fill=white)
        for j in range(4):d.line((283,y+15+j*34,433,y+15+j*34),fill=accent if j==0 else muted,width=8)
        d.text((300,y+151),'PDF',font=font(27),fill=bg)
    elif kind=='chat':
        d.rounded_rectangle((123,y-20,526,y+71),radius=20,fill=accent)
        d.polygon([(160,y+65),(183,y+65),(160,y+93)],fill=accent)
        d.rounded_rectangle((205,y+95,594,y+188),radius=20,fill=bg,outline=white,width=2)
        d.text((151,y+5),'BUREAU',font=font(25),fill=white)
        d.text((233,y+121),'CHAUFFEUR',font=font(25),fill=white)
    elif kind=='calendar':
        d.rounded_rectangle((142,y-20,581,y+192),radius=16,fill=bg,outline=accent,width=3)
        d.rectangle((142,y-20,581,y+24),fill=accent)
        for j,label in enumerate(['MISSION','CHAUFFEUR','DOCUMENTS']):
            d.rectangle((166,y+45+j*45,187,y+66+j*45),fill=accent)
            d.text((208,y+40+j*45),label,font=font(22),fill=white)
    elif kind=='stairs':
        for j in range(4):d.rectangle((155+j*82,y+130-j*44,237+j*82,y+190),fill=accent)
        d.rectangle((392,y-10,486,y+83),fill=bg,outline=white,width=4)
        d.line((438,y-10,438,y+35),fill=white,width=4)
    elif kind=='boxes':
        for x,yy,side in [(140,y+50,110),(280,y-4,145),(452,y+65,100)]:
            d.rounded_rectangle((x,yy,x+side,yy+side),radius=8,fill=bg,outline=accent,width=4)
            d.line((x+side//2,yy,x+side//2,yy+side//2),fill=white,width=5)
        d.line((135,y+193,568,y+193),fill=muted,width=3)
    elif kind=='offers':
        for j in range(2):
            x=124+j*250;d.rounded_rectangle((x,y-8,x+222,y+172),radius=16,fill=bg,outline=accent,width=3)
            d.text((x+20,y+22),'OFFRE '+('A' if j==0 else 'B'),font=font(23),fill=white)
            d.text((x+20,y+100),'PRIVÉE',font=font(22),fill=muted)
    elif kind=='steps':
        labels={'urgent':['DÉCRIRE','ÉTUDIER','CONFIRMER'],'mon_exploit':['MISSION','DOCUMENTS','ÉCHANGES'],'chronoss':['DÉCRIRE','ÉTUDIER','DEVIS']}[topic['service']]
        for j,label in enumerate(labels):
            yy=y-15+j*70;d.rounded_rectangle((130,yy,588,yy+53),radius=12,fill=bg,outline=accent,width=2)
            d.ellipse((147,yy+10,181,yy+44),fill=accent)
            d.text((155,yy+13),str(j+1),font=font(18),fill=white)
            d.text((208,yy+12),label,font=font(23),fill=white)
    else:
        d.line((158,y+83,570,y+83),fill=muted,width=8)
        for x in [158,570]:d.ellipse((x-17,y+66,x+17,y+100),fill=accent)
        d.rounded_rectangle((275,y+20,400,y+94),radius=10,fill=accent)
        d.rectangle((400,y+43,442,y+94),fill=white)
        for x in [303,418]:d.ellipse((x-14,y+81,x+14,y+109),fill=bg,outline=muted,width=3)
    body=topic['body']
    labels=topic.get('scene_labels') or []
    if phase==1 and len(labels)>1 and len(labels[1])<180:body=labels[1]
    lines=wrapped(d,body,24,x2-x1-50,False)
    if len(lines)>5:lines=wrapped(d,body,21,x2-x1-50,False)
    if len(lines)>6:raise ValueError('business_body_overflows')
    for j,line in enumerate(lines):d.text((x1+24,y1+447+j*30),line,font=font(24 if len(lines)<=5 else 21,False),fill=white)
    d.text((x1+24,y2-36),'Exemple illustratif · aucune mission réelle',font=font(15,False),fill=muted)
    im.save(path)
    return kind

def render(topic,day,slot,outputdir,**kwargs):
    if isinstance(day,str):day=date.fromisoformat(day)
    output=Path(outputdir);output.mkdir(parents=True,exist_ok=True)
    if topic.get('service') not in SOURCES or not topic.get('cta_url','').startswith('https://13urgent.fr/'):raise ValueError('topic_not_authorized')
    cache=Path(os.environ.get('MARKETING_MEDIA_CACHE',str(output.parent/'approved-sources')))
    source=source_for(topic['service'],cache)
    music=MUSIC_LOCAL if MUSIC_LOCAL.exists() else fetch(os.environ.get('MARKETING_MUSIC_URL',MUSIC_URL),cache/'original-background.wav')
    info=probe(source);duration=float(info['format']['duration']);video_stream=next(s for s in info['streams'] if s['codec_type']=='video')
    audio_stream=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
    if not audio_stream:raise RuntimeError('approved_voice_missing')
    source_metrics=audio_metrics(source)
    if source_metrics['mean_db'] < -45:raise RuntimeError('approved_voice_silent')
    bg,panel,accent,white,muted=PALETTES[int(topic.get('palette',0))%4]
    style=int(topic.get('visual_style',0))%4
    canvas=Image.new('RGB',(720,1280),bg);draw=ImageDraw.Draw(canvas)
    draw.ellipse((470,-250,1100,400),fill=panel)
    if style==1:draw.rectangle((0,0,16,1280),fill=accent)
    if style==2:
        for offset in range(4):draw.line((0,1150+offset*40,720,950+offset*40),fill=panel,width=20)
    if style==3:draw.rounded_rectangle((26,28,694,220),radius=20,fill=panel)
    draw.text((42,44),topic['brand'],font=font(34),fill=accent)
    hook_lines=wrapped(draw,topic['hook'],38,630)
    if len(hook_lines)>3:raise ValueError('hook_overflows')
    for index,line in enumerate(hook_lines):draw.text((42,102+index*45),line,font=font(38),fill=white)
    pane=(32,254,688,960) if style%2==0 else (44,254,676,960)
    draw.rounded_rectangle(pane,radius=22,fill=panel,outline=accent,width=2)
    maxw=pane[2]-pane[0]-18;maxh=pane[3]-pane[1]-18
    factor=min(maxw/video_stream['width'],maxh/video_stream['height'])
    vw=max(2,int(video_stream['width']*factor)//2*2);vh=max(2,int(video_stream['height']*factor)//2*2)
    x=(720-vw)//2;y=pane[1]+(pane[3]-pane[1]-vh)//2
    conditions={'urgent':'PROFESSIONNELS · OFFRES SELON CAPACITÉS','mon_exploit':'DÉCOUVREZ LE PARCOURS · ESSAI SUR DEMANDE','chronoss':'PARTICULIERS · ÉTUDE ET DEVIS AVANT ENGAGEMENT'}
    small=conditions[topic['service']]
    for index,line in enumerate(wrapped(draw,small,18,625)):draw.text((42,993+index*23),line,font=font(18),fill=muted)
    draw.text((42,1054),'13urgent.fr',font=font(38),fill=white)
    path=urlsplit(topic['cta_url']).path
    draw.text((42,1106),path,font=font(25),fill=accent)
    draw.text((42,1190),'Présentation du service · aucune donnée client',font=font(16,False),fill=muted)
    overlay=output/'layout.png';canvas.save(overlay)
    scenes=[output/'business-panel-1.png',output/'business-panel-2.png']
    business_kinds=[business_panel(topic,pane,PALETTES[int(topic.get('palette',0))%4],i,path) for i,path in enumerate(scenes)]
    target=output/f'{topic["id"]}-{day:%Y%m%d}-s{slot}.mp4'
    afade=max(0,duration-1.2)
    s1=duration*.26;e1=s1+3.3;s2=duration*.60;e2=min(duration-1,s2+3.5)
    filters=(f'[0:v]scale={vw}:{vh},fps=24,setsar=1[master];[1:v][master]overlay={x}:{y}:shortest=1[base];'
             f"[base][3:v]overlay=x='max(0,720-(t-{s1})*1440)':y=0:enable='between(t,{s1},{e1})'[step1];"
             f"[step1][4:v]overlay=x='min(0,-720+(t-{s2})*1440)':y=0:enable='between(t,{s2},{e2})',fps=24,format=yuv420p[v];"
             '[0:a]aresample=48000,loudnorm=I=-16:TP=-2:LRA=7,asplit=2[voice][side];'
             f'[2:a]aresample=48000,volume=0.22,afade=t=in:d=0.6,afade=t=out:st={afade}:d=1.2[bed];'
             '[bed][side]sidechaincompress=threshold=0.10:ratio=3:attack=20:release=300[ducked];'
             '[voice][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-loop','1','-i',str(overlay),'-stream_loop','-1','-i',str(music),'-loop','1','-i',str(scenes[0]),'-loop','1','-i',str(scenes[1]),'-filter_complex',filters,'-map','[v]','-map','[a]','-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','23','-threads','2','-c:a','aac','-b:a','128k','-ar','48000','-ac','2','-movflags','+faststart',str(target)],check=True)
    result=probe(target);vs=next(s for s in result['streams'] if s['codec_type']=='video');audio=next((s for s in result['streams'] if s['codec_type']=='audio'),None)
    measured=audio_metrics(target)
    if (vs['width'],vs['height'],vs['codec_name'])!=(720,1280,'h264') or not audio or audio['codec_name']!='aac' or measured['mean_db'] < -35 or abs(float(result['format']['duration'])-duration)>.15:raise RuntimeError('render_verification_failed')
    correlation=voice_correlation(source,target)
    if correlation<0.65:raise RuntimeError('approved_voice_not_preserved_in_mix')
    cover=output/'cover.jpg';subprocess.run(['ffmpeg','-v','error','-y','-ss','1','-i',str(target),'-frames:v','1',str(cover)],check=True)
    manifest={'schema_version':2,'topic_id':topic['id'],'service':topic['service'],'editorial_date':day.isoformat(),'slot':slot,'video_file':target.name,'duration_seconds':duration,'width':720,'height':1280,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'voice':{'present':True,'source_url':SOURCES[topic['service']]['url'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_metrics':source_metrics,'content_and_tempo_preserved':True,'correlation_to_approved_source':correlation,'new_voice_generation':False},'music':{'kind':'previously_approved_original_instrumental','url':MUSIC_URL,'volume_factor_before_ducking':0.22,'ducked_under_speech':True,'paid_music':False,'verified_trend':False},'audio_metrics':measured,'visual_style':style,'business_diagrams':business_kinds,'animated_business_panels':True,'palette':topic.get('palette',0),'cta_url':topic['cta_url'],'client_data':False,'ai_disclosure_required':True,'publication_status':'not_published','limitations':['Prepared editorial rotation, not autonomous live trend research.','Voice is a preexisting approved general presentation matched to the service, not newly synthesized per hook.']}
    mp=output/'manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (output/'caption-linkedin.txt').write_text(topic['linkedin']+'\n');(output/'caption-tiktok.txt').write_text(topic['tiktok']+'\n')
    return {'video':str(target),'manifest':str(mp),'cover':str(cover),'duration':duration,'topic_id':topic['id']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--catalogue',type=Path,default=ROOT/'rotation_catalogue.json');parser.add_argument('--index',type=int,default=0);parser.add_argument('--date',required=True);parser.add_argument('--slot',type=int,default=0);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    topic=json.loads(args.catalogue.read_text())['topics'][args.index]
    print(json.dumps(render(topic,args.date,args.slot,args.output),ensure_ascii=False))

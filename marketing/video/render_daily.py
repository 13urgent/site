#!/usr/bin/env python3
"""Render a 20-second original social explainer. No external services or clients.

Dependencies: Python 3.11+, Pillow, ffmpeg, ffprobe, DejaVu Sans fonts.
The capsule is an illustration of the verified product journey, not a live UI
recording. Music is synthesized here: no sampled recordings or existing songs.
"""
from __future__ import annotations

import argparse
import array
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS, DURATION = 1080, 1920, 24, 20
BG, PANEL, RED, WHITE, MUTED = '#0c1120', '#172238', '#ed263d', '#f5f7fb', '#b6c2d7'
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')


def font(size: int, bold: bool = True):
    return ImageFont.truetype(str(FONT_ROOT / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)


def wrapped(draw, text, size, width, bold=True):
    result = []
    for paragraph in text.split('\n'):
        current = ''
        for word in paragraph.split():
            proposed = (current + ' ' + word).strip()
            if draw.textlength(proposed, font=font(size, bold)) > width and current:
                result.append(current)
                current = word
            else:
                current = proposed
        result.append(current)
    return result


def block(draw, xy, value, size, color=WHITE, bold=True, gap=12, max_width=830):
    x, y = xy
    for line in wrapped(draw, value, size, max_width, bold):
        if draw.textlength(line, font=font(size, bold)) > max_width:
            raise ValueError('A word cannot fit in the safe text region')
        draw.text((x, y), line, font=font(size, bold), fill=color)
        y += size + gap
    return y


def rr(draw, box, fill=PANEL, radius=28, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def route(draw, y):
    draw.line((194, y+95, 806, y+95), fill='#4c5d7b', width=12)
    draw.ellipse((170, y+71, 218, y+119), fill=RED)
    draw.ellipse((782, y+71, 830, y+119), fill=WHITE)
    rr(draw, (416, y+39, 584, y+104), RED, radius=12)
    draw.polygon([(584,y+60),(624,y+60),(650,y+104),(584,y+104)], fill=WHITE)
    for x in [453, 602]:
        draw.ellipse((x-17,y+90,x+17,y+124),fill=BG,outline=MUTED,width=4)


def illustration(draw, kind, labels, topic_index):
    x1, y1, x2, y2 = 96, 870, 924, 1460
    rr(draw, (x1,y1,x2,y2), PANEL, 36, '#30415e')
    block(draw, (132,906), 'LE PARCOURS EN BREF', 26, MUTED, max_width=730)
    if kind in ['route','truck']:
        route(draw, 970)
    elif kind == 'boxes':
        for x,y,size in [(208,1012,100),(337,977,135),(497,1027,86),(610,997,115)]:
            rr(draw,(x,y,x+size,y+size), '#243652',12, RED)
            draw.line((x+size//2,y,x+size//2,y+size//2), fill=MUTED,width=7)
    elif kind == 'document':
        rr(draw, (404,973,614,1158), '#f5f7fb', 16)
        for j in range(4):
            draw.line((437,1017+j*28,580,1017+j*28),fill=RED if j==0 else '#8491a6',width=8)
    elif kind == 'offers':
        for j in range(2):
            rr(draw,(173+j*352,991,484+j*352,1158),'#22334d',18,RED if j==1 else '#526582')
            block(draw,(204+j*352,1020),'OFFRE '+('A' if j==0 else 'B'),25,max_width=250)
            block(draw,(204+j*352,1080),'PRIVÉE',29,RED,max_width=250)
    elif kind == 'cta':
        rr(draw,(166,996,855,1144),RED,24)
        block(draw,(224,1027),'13urgent.fr',70,max_width=590)
    else:
        for j in range(3):
            rr(draw,(171,982+j*62,851,1026+j*62),'#243652',9)
            draw.line((198,1004+j*62,450+j*90,1004+j*62),fill='#92a3c2',width=6)
    for j,label in enumerate(labels):
        y=1210+j*69
        draw.ellipse((140,y+5,165,y+30),fill=RED)
        block(draw,(188,y),label,29,WHITE,bold=False,max_width=690,gap=4)
    block(draw,(112,1485),'Illustration du parcours · aucune donnée client',20,MUTED,False,max_width=800)


def slide(scene, index, audience, logo, destination):
    image = Image.new('RGB',(W,H),BG)
    d=ImageDraw.Draw(image)
    d.ellipse((650,-250,1460,580), fill='#161d30')
    d.line((98,318,920,318),fill='#35415a',width=2)
    mark=logo.copy(); mark.thumbnail((420,170),Image.Resampling.LANCZOS)
    if mark.mode=='RGBA': image.paste(mark,(92,125),mark)
    else: image.paste(mark,(92,125))
    block(d,(576,158),'PAR CHRONOSS',24,MUTED,max_width=350)
    block(d,(576,204),'MODE D’EMPLOI',24,WHITE,max_width=350)
    # Every substantive text item stays in the left/central safe zone. The right
    # 12% and the bottom 250px are free of substantive information for TikTok UI.
    end=block(d,(100,359),scene['eyebrow'],27,RED,max_width=825)
    if end>455: raise ValueError('Eyebrow is too tall')
    title_size=next((size for size in (68,64,60,56,52) if len(wrapped(d,scene['title'],size,830))*(size+16)<=220),None)
    if title_size is None: raise ValueError('Title is too tall')
    end=block(d,(96,475),scene['title'],title_size,max_width=830,gap=16)
    if end>695: raise ValueError('Title is too tall')
    end=block(d,(100,718),scene['body'],32,MUTED,False,max_width=825,gap=12)
    if end>865: raise ValueError('Body collides with illustration')
    illustration(d,scene['icon'],scene['labels'],index)
    block(d,(100,1580),'13urgent.fr',42,WHITE,max_width=800)
    block(d,(100,1647),audience,25,MUTED,False,max_width=800)
    for j in range(5):
        rr(d,(100+j*164,1714,240+j*164,1722),RED if j<=index else '#34415b',4)
    image.save(destination, quality=95)
    return image


def original_music(path, day):
    """A deterministic instrumental cue generated from oscillators, no samples.

    Four harmonically simple chords and synthesized drums. This is an original
    backing track, not a verified trend or imitation of any identified artist.
    """
    sr=48000
    bpm=102+(day.toordinal()%4)*2
    beat=60/bpm
    chords=[(130.8128,164.8138,195.9977),(110,130.8128,164.8138),
            (87.3071,110,130.8128),(97.9989,123.4708,146.8324)]
    samples=array.array('h')
    seed=day.toordinal() & 0xffffffff
    for n in range(sr*DURATION):
        t=n/sr
        b=t/beat
        chord=chords[int(b//4)%4]
        phase=b%1
        bass=.12*math.sin(2*math.pi*(chord[0]/2)*t)*math.exp(-phase*4)
        pad=sum(math.sin(2*math.pi*f*t) for f in chord)*.026
        arp_freq=chord[int(b*2)%3]*2
        arp=.065*math.sin(2*math.pi*arp_freq*t)*math.exp(-(b*2%1)*8)
        kick=.24*math.sin(2*math.pi*(46*(t%beat)+2.1*(1-math.exp(-(t%beat)*35))))*math.exp(-(t%beat)*21)
        seed=(1664525*seed+1013904223)&0xffffffff
        noise=(seed/0xffffffff)*2-1
        half_phase=(b*2%1)*beat/2
        hat=noise*.045*math.exp(-half_phase*140)
        snare=noise*.08*math.exp(-(t%beat)*45) if int(b)%2 else 0
        envelope=min(1,t/.5,max(0,(DURATION-t)/1.1))
        value=(bass+pad+arp+kick+hat+snare)*envelope
        value=max(-.9,min(.9,value))
        sample=int(value*32767)
        samples.extend([sample,sample])
    if __import__('sys').byteorder!='little': samples.byteswap()
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(sr);stream.writeframes(samples.tobytes())
    return bpm


def validate_topic(topic):
    if len(topic['scenes']) != 5: raise ValueError('Exactly five scenes are required')
    if not topic['url'].startswith('https://13urgent.fr/'): raise ValueError('Unexpected CTA destination')
    for scene in topic['scenes']:
        if len(scene['labels'])!=3: raise ValueError('Each scene requires three labels')


def render(topic_key, day, output, topic_override=None):
    topics=json.loads((ROOT/'topics.json').read_text())
    if topic_override is None and topic_key not in topics: raise ValueError('Unknown topic')
    topic=topic_override if topic_override is not None else topics[topic_key];validate_topic(topic)
    output.mkdir(parents=True,exist_ok=True)
    assets=output/'frames';assets.mkdir(exist_ok=True)
    logo=Image.open(ROOT/'assets/logo-13urgent-web.png').convert('RGBA')
    for i,scene in enumerate(topic['scenes']):
        slide(scene,i,topic['audience'],logo,assets/f'scene-{i}.png')
    concat=assets/'slides.txt'
    concat.write_text(''.join(f"file 'scene-{i}.png'\nduration 4\n" for i in range(5))+"file 'scene-4.png'\n")
    music=output/'musique-originale.wav';bpm=original_music(music,day)
    video=output/f'13urgent-{topic_key}-{day:%Y%m%d}.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-i',str(music),'-vf',f'fps={FPS},format=yuv420p','-af','loudnorm=I=-18:TP=-2:LRA=7','-t',str(DURATION),'-c:v','libx264','-preset','veryfast','-threads','2','-crf','21','-c:a','aac','-b:a','160k','-ar','48000','-movflags','+faststart',str(video)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
    vs=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    if (vs['width'],vs['height'],vs['codec_name'],vs['pix_fmt']) != (1080,1920,'h264','yuv420p'): raise ValueError('Video encoding did not match the required delivery format')
    if audio['codec_name']!='aac' or audio['channels']!=2: raise ValueError('Audio encoding did not match the required delivery format')
    if abs(float(probe['format']['duration'])-DURATION)>.1: raise ValueError('Unexpected rendered duration')
    (output/'verification-ffprobe.json').write_text(json.dumps(probe,indent=2)+'\n')
    (output/'caption.txt').write_text(topic['caption']+'\n')
    manifest={'schema_version':1,'date':day.isoformat(),'topic':topic_key,'audience':topic['audience'],'video_file':video.name,'duration_seconds':DURATION,'width':W,'height':H,'fps':FPS,'codec':'H.264/AAC','voiceover':False,'caption':topic['caption'],'destination':topic['url'],'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'music':{'kind':'original_synthesized_instrumental','bpm':bpm,'external_samples':False,'commercial_trend_verified':False,'source':'render_daily.py / original_music','restrictions':'Do not label this cue as a trending song. No existing recording or named artist has been used.'},'visuals':{'kind':'illustrated_product_journey','live_screen_recording':False,'client_data':False,'logo_source':'CHRONOSS / 13 URGENT official logo supplied with project'},'editorial_review':{'claim_scope':'Current product journey only; no guaranteed availability, revenue, attribution or number of users','pending':'Editorial supervisor must check this topic against current product before scheduling'},'render_verification':'ffprobe technical properties passed','publication_status':'not_published'}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    storyboard=Image.new('RGB',(1080,384),BG)
    for i in range(5):
        frame=Image.open(assets/f'scene-{i}.png');frame.thumbnail((216,384));storyboard.paste(frame,(i*216,0))
    storyboard.save(output/'storyboard.jpg',quality=93)
    Image.open(assets/'scene-0.png').save(output/'cover.jpg',quality=95)
    print(json.dumps({'video':str(video),'manifest':str(output/'manifest.json'),'topic':topic_key,'date':day.isoformat(),'verified':True},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',required=True,help='Paris editorial date, YYYY-MM-DD')
    parser.add_argument('--topic',default='auto',choices=['auto','donneurs_ordre','transporteurs','documents','particuliers'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    day=date.fromisoformat(args.date)
    topic=args.topic
    if topic=='auto': topic=list(json.loads((ROOT/'topics.json').read_text()))[day.toordinal()%4]
    render(topic,day,args.output.resolve())

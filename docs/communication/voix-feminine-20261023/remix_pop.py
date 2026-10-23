from pathlib import Path
import subprocess,json,hashlib
R=Path('/workspace/13urgent-social-voix-naturelle-20261023');P=R/'production';O=R/'livraison'
# Bande instrumentale originale de la vidéo commerciale du projet, documentée sans voix off.
source=Path('/tmp/13urgent-publication-cleanup/videos/commerciales/donneurs-ordre.mp4')
subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-vn','-t','25','-af','loudnorm=I=-20:TP=-3:LRA=7,aresample=48000,afade=t=out:st=23.8:d=1.2','-c:a','pcm_s16le',str(P/'musique-pop.wav')],check=True)
filters='[1:a]loudnorm=I=-16:TP=-2:LRA=7,aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][det];[2:a]asplit=2[bed][up];[bed][det]sidechaincompress=threshold=0.12:ratio=1.5:attack=20:release=250[duck];[v][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.82:level=0[a];[up]anullsink'
file=O/'donneurs-ordre-femme-pop-v3.mp4'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(O/'donneurs-ordre-voix-feminine.mp4'),'-i',str(P/'narration-feminine.wav'),'-i',str(P/'musique-pop.wav'),'-filter_complex',filters,'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','25','-movflags','+faststart',str(file)],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(P/'musique-pop.wav'),'-c:a','libmp3lame','-b:a','192k',str(O/'musique-pop-seule.mp3')],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(file),'-f','null','-'],check=True)
meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)]));assert abs(float(meta['format']['duration'])-25)<.1
(O/'VERIFICATION-POP.json').write_text(json.dumps({'duration':25,'decode':'PASS','sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'music':'Bande pop instrumentale originale de la vidéo commerciale CHRONOSS, sans voix off','music_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'music_target_LUFS':-20,'voice_target_LUFS':-16},indent=2))
p=O/'index.html';s=p.read_text().replace('donneurs-ordre-voix-feminine-musique.mp4','donneurs-ordre-femme-pop-v3.mp4').replace('une musique instrumentale plus audible','une bande pop instrumentale plus présente');s=s.replace('<h2>Écouter la voix seule</h2>','<p><a href="musique-pop-seule.mp3">Écouter la musique seule</a></p><h2>Écouter la voix seule</h2>');p.write_text(s)
print('PASS vidéo pop et musique seule prêtes',flush=True)

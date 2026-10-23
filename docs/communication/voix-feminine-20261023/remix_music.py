"""Remonte la musique et la baisse automatiquement pendant la voix, sans réencoder l’image."""
from pathlib import Path
import subprocess
R=Path('/workspace/13urgent-social-voix-naturelle-20261023');O=R/'livraison';P=R/'production';BASE=Path('/workspace/13urgent-social-20261023/production')
mix='[1:a]loudnorm=I=-16:TP=-2:LRA=7,aresample=48000,asplit=2[v][det];[2:a]loudnorm=I=-23:TP=-5:LRA=7,aresample=48000,afade=t=in:d=0.4,afade=t=out:st=23.5:d=1.5[m];[m][det]sidechaincompress=threshold=0.08:ratio=3:attack=25:release=400[duck];[v][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.88:level=0[a]'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(O/'donneurs-ordre-voix-feminine.mp4'),'-i',str(P/'narration-feminine.wav'),'-i',str(BASE/'musique-originale.wav'),'-filter_complex',mix,'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','25','-movflags','+faststart',str(O/'donneurs-ordre-voix-feminine-musique.mp4')],check=True)
print('TERMINE version musique audible et voix inchangée',flush=True)

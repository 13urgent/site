"""Build browser icons from the existing company logo and retain head links."""
from pathlib import Path
import sys
from PIL import Image, ImageOps

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
LINKS='<link rel="icon" type="image/png" sizes="64x64" href="/assets/favicon-13urgent-64.png?v=20261120"><link rel="icon" type="image/x-icon" href="/favicon.ico?v=20261120"><link rel="apple-touch-icon" href="/assets/favicon-13urgent-192.png?v=20261120">'
source=Image.open(ROOT/'assets/logo-13urgent-web.png').convert('RGBA')
source=source.crop(source.getbbox())
canvas=Image.new('RGBA',(512,512),(255,255,255,0))
logo=ImageOps.contain(source,(512,512),Image.Resampling.LANCZOS)
canvas.alpha_composite(logo,((512-logo.width)//2,(512-logo.height)//2))
canvas.save(ROOT/'favicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128)])
for size in (64,192):canvas.resize((size,size),Image.Resampling.LANCZOS).save(ROOT/f'assets/favicon-13urgent-{size}.png')
for p in [*ROOT.glob('*.html'),ROOT/'tools/site-template.html',ROOT/'tools/build_terms.py']:
    if not p.is_file():continue
    content=p.read_text()
    if '<head>' in content and '/assets/favicon-13urgent-64.png' not in content:
        p.write_text(content.replace('<head>','<head>'+LINKS,1))
print('Company browser icons and page links ready.')

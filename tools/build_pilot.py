"""Construit le site statique professionnel, sans documents de test ni clés privées."""
from pathlib import Path
import argparse
import re
import shutil
from build_admin import build_admin

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--open-registration', action='store_true', help='Ouvrir les demandes professionnelles ; ne change pas le mode commercial en base.')
args = parser.parse_args()
output = Path(args.output).resolve()
if output == root or root in output.parents or output in root.parents:
    raise SystemExit('Le dossier de sortie doit être séparé du dépôt source.')
output.mkdir(parents=True, exist_ok=True)
if any(output.iterdir()):
    raise SystemExit('Le dossier de sortie doit être vide pour préserver les fichiers existants.')
files = ['index.html','style.css','config.js','auth.js','app.js','marketplace.js','manual-commerce.js','conditions-professionnelles.html','conditions-professionnelles-v3.html','conditions-professionnelles-v4.html','mentions-legales.html','confidentialite.html','billing.js','documents.js','imports.js','terms-links.js','audience.js','audience.css','google-ads.js','support.js','support-knowledge.js','support.css','document-assistant.js','robots.txt','sitemap.xml']
for name in files:
    shutil.copy2(root / name, output / name)
(output / 'admin.html').write_text(build_admin())
(output / 'assets').mkdir()
shutil.copy2(root / 'assets/logo-13urgent-web.png', output / 'assets/logo-13urgent-web.png')
config = (output / 'config.js').read_text()
config, count = re.subn(r'window\.URGENT_MARKETPLACE_PILOT\s*=\s*false\s*;', 'window.URGENT_MARKETPLACE_PILOT = true;', config)
if count != 1:
    raise SystemExit('Activation explicite du pilote introuvable dans config.js.')
config, billing_count = re.subn(r'window\.URGENT_BILLING_TEST_UI\s*=\s*(?:true|false)\s*;', 'window.URGENT_BILLING_TEST_UI = false;', config)
if billing_count != 1:
    raise SystemExit('Commutateur des paiements de test introuvable dans config.js.')
config += '\n// Ouverture des demandes professionnelles distincte des droits et du mode commercial.\nwindow.URGENT_ALLOW_REGISTRATION = '+('true' if args.open_registration else 'false')+';\n'
(output / 'config.js').write_text(config)
html = (output / 'index.html').read_text()
if not args.open_registration:
    html = html.replace('Connexion / inscription', 'Connexion au pilote')
(output / 'index.html').write_text(html)
if (root / 'CNAME').exists():
    shutil.copy2(root / 'CNAME', output / 'CNAME')
(output / '.nojekyll').write_text('')
print('Version créée : paiement Stripe désactivé, inscriptions '+('ouvertes aux demandes professionnelles' if args.open_registration else 'masquées')+', aucune pièce justificative copiée. Le mode commercial reste contrôlé en base.')

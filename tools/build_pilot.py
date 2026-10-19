"""Construit un site statique pilote, sans documents de test ni clés privées."""
from pathlib import Path
import argparse
import re
import shutil

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
output = Path(args.output).resolve()
if output == root or root in output.parents or output in root.parents:
    raise SystemExit('Le dossier de sortie doit être séparé du dépôt source.')
output.mkdir(parents=True, exist_ok=True)
if any(output.iterdir()):
    raise SystemExit('Le dossier de sortie doit être vide pour préserver les fichiers existants.')
files = ['index.html','style.css','config.js','auth.js','app.js','marketplace.js','billing.js','documents.js','imports.js']
for name in files:
    shutil.copy2(root / name, output / name)
(output / 'assets').mkdir()
shutil.copy2(root / 'assets/logo-13urgent-web.png', output / 'assets/logo-13urgent-web.png')
config = (output / 'config.js').read_text()
config, count = re.subn(r'window\.URGENT_MARKETPLACE_PILOT\s*=\s*false\s*;', 'window.URGENT_MARKETPLACE_PILOT = true;', config)
if count != 1:
    raise SystemExit('Activation explicite du pilote introuvable dans config.js.')
config, billing_count = re.subn(r'window\.URGENT_BILLING_TEST_UI\s*=\s*(?:true|false)\s*;', 'window.URGENT_BILLING_TEST_UI = false;', config)
if billing_count != 1:
    raise SystemExit('Commutateur des paiements de test introuvable dans config.js.')
config += '\n// Le pilote public utilise les comptes existants ; aucun paiement.\nwindow.URGENT_ALLOW_REGISTRATION = false;\n'
(output / 'config.js').write_text(config)
html = (output / 'index.html').read_text()
html = html.replace('<head>', '<head><meta name="robots" content="noindex,nofollow">', 1)
html = html.replace('Connexion / inscription', 'Connexion au pilote')
(output / 'index.html').write_text(html)
(output / '.nojekyll').write_text('')
(output / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
print('Version pilote créée : paiements désactivés, inscription masquée, aucune pièce justificative copiée.')

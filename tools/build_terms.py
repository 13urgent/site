"""Produit les conditions HTML à partir du document relu, sans notes internes."""
from pathlib import Path
from html import escape
import re
root=Path(__file__).resolve().parents[1]
s=(root/'docs/juridique/CGU-CGV-PROJET.md').read_text()
s=s[s.index('## 1. Exploitant'):s.index('## Contrôles avant mise en application')]
# Les mentions de contrôle documentaire restent dans le dossier interne.
s=s.replace(' (non mentionné dans l’extrait fourni ; rattachement de l’établissement à confirmer)','')
s=s.replace(', communiqué par l’exploitant','')
version='PRO-B2B-2026-10-20-v3'
def inline(line):
 return re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',escape(line))
blocks=[];paragraph=[];in_list=False;table=[]
def flush():
 global paragraph,in_list,table
 if paragraph:blocks.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph=[]
 if in_list:blocks.append('</ul>');in_list=False
 if table:
  rows=[row for row in table if not re.fullmatch(r'[|\s:\-]+',row)]
  blocks.append('<div class="table-wrap"><table>')
  for n,row in enumerate(rows):
   tag='th' if n==0 else 'td';blocks.append('<tr>'+''.join(f'<{tag}>'+inline(c.strip())+f'</{tag}>' for c in row.strip('|').split('|'))+'</tr>')
  blocks.append('</table></div>');table=[]
for line in s.splitlines():
 if line.startswith('|'):
  if paragraph or in_list:flush()
  table.append(line);continue
 if line.startswith('## '):flush();blocks.append('<h2>'+inline(line[3:])+'</h2>')
 elif line.startswith('- '):
  if paragraph or table:flush()
  if not in_list:blocks.append('<ul>');in_list=True
  blocks.append('<li>'+inline(line[2:])+'</li>')
 elif not line.strip():flush()
 else:
  if in_list or table:flush()
  paragraph.append(line)
flush()
page='''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Conditions professionnelles — 13 URGENT / CHRONOSS</title><style>body{font-family:Arial,sans-serif;color:#171923;line-height:1.65;margin:0;background:#f7f7f8}main{max-width:940px;margin:auto;padding:32px 22px}h1,h2{line-height:1.3}h2{margin-top:36px}a{color:#aa1524}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:10px;text-align:left}.table-wrap{overflow:auto}.notice{padding:18px;background:#fff0d6;border-left:4px solid #c52132}@media print{body{background:white}nav{display:none}h2{break-after:avoid}tr{break-inside:avoid}}</style></head><body><main><nav><a href="./">Retour au site</a></nav><h1>Conditions professionnelles 13 URGENT</h1><p>Exploitant : CHRONOSS — Version '''+version+'''</p><p class="notice">Conditions du service commercial, applicables lors de son activation et après acceptation expresse. Le pilote gratuit et les exercices fictifs n’entraînent aucun frais rétroactif. Vous pouvez enregistrer cette page et l’imprimer en PDF depuis votre navigateur.</p>'''+''.join(blocks)+'</main></body></html>'
versioned=root/'conditions-professionnelles-v3.html'
if versioned.exists() and versioned.read_text()!=page:
    raise SystemExit('La version v3 existe avec un autre contenu : créer une nouvelle version au lieu de réécrire les conditions déjà acceptées.')
versioned.write_text(page)
(root/'conditions-professionnelles.html').write_text(page)
print('Conditions HTML préparées : '+version)

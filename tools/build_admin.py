"""Construit la page d’administration distincte à partir de la présentation partagée."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def build_admin():
    page=(root/'index.html').read_text()
    page=page.replace('<body>', '<body data-admin-page="true">',1)
    page=page.replace('<meta name="robots" content="index,follow">','<meta name="robots" content="noindex,nofollow">')
    page=page.replace('<title>13 URGENT — Transport express entre professionnels</title>','<title>Administration — 13 URGENT</title>')
    page=page.replace('<main id="accueil">','<p id="adminPageNotice" class="notice" role="status">Connectez-vous avec votre compte administrateur pour accéder à la gestion.</p><main id="accueil">')
    page=page.replace('<script src="https://cdn.jsdelivr.net', (root/'tools/admin-dialog.html').read_text()+'<script src="https://cdn.jsdelivr.net',1)
    return page
if __name__=='__main__':
    (root/'admin.html').write_text(build_admin())

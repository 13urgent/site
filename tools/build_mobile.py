"""Génère l'application installable à partir des composants du site, sans comptes distincts."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def build_mobile():
    page=(root/'tools/site-template.html').read_text()
    page=page.replace('<body>','<body data-mobile-app="true" data-mobile-view="missions">',1)
    page=page.replace('<title>13 URGENT — Transport express entre professionnels</title>','<title>Application mobile — 13 URGENT</title>')
    page=page.replace('<meta name="robots" content="index,follow">','<meta name="robots" content="noindex,follow">')
    page=page.replace('</head>','<link rel="manifest" href="mobile.webmanifest"><link rel="apple-touch-icon" href="assets/mobile-icon-192.png"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="13 URGENT"><meta name="apple-mobile-web-app-status-bar-style" content="default"></head>',1)
    toolbar='<section class="mobile-toolbar" aria-label="Votre application"><h1>13 URGENT dans votre poche</h1><p>Vos courses, vos documents et votre suivi professionnel.</p><button id="mobileDocuments" class="btn secondary" type="button">Mes justificatifs</button><button id="mobileAccount" class="btn secondary" type="button">Mon compte</button><button id="mobileRefresh" class="btn secondary" type="button">Actualiser</button><button id="mobileInstall" class="btn primary" type="button" hidden>Installer l’application</button><p id="mobileStatus" role="status"></p><p class="mobile-install-help">Sur iPhone : ouvrez cette page dans Safari, puis Partager → Sur l’écran d’accueil. Sur Android : utilisez « Installer l’application » ou le menu du navigateur.</p></section><p id="mobileOffline" class="mobile-offline" role="status" hidden>Hors connexion : reconnectez-vous pour consulter et envoyer les données de votre compte.</p>'
    page=page.replace('<main id="accueil">',toolbar+'<main id="accueil">',1)
    nav='<p class="mobile-help"><a href="confidentialite.html" target="_blank" rel="noopener">Confidentialité</a><a href="conditions-professionnelles-v4.html" target="_blank" rel="noopener">Conditions professionnelles</a><a href="mailto:contact@13urgent.fr">Nous contacter</a></p><nav class="mobile-tabs" aria-label="Navigation de l’application"><button type="button" data-mobile-view-button="missions" aria-current="page">Mes courses</button><button type="button" data-mobile-view-button="courses">Disponibles</button><button type="button" data-mobile-view-button="publish">Déposer</button><button type="button" data-mobile-view-button="plans">Forfaits transporteur</button></nav>'
    page=page.replace('</body>','<script src="mobile.js?v=20261029-mobile"></script>'+nav+'</body>',1)
    # Le script doit lire une barre de navigation déjà présente.
    page=page.replace('<script src="mobile.js?v=20261029-mobile"></script>'+nav,nav+'<script src="mobile.js?v=20261029-mobile"></script>')
    return page
if __name__=='__main__':(root/'mobile.html').write_text(build_mobile())

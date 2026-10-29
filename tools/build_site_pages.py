"""Pages publiques distinctes partageant les composants métier existants.

Les composants hors rubrique restent masqués pour préserver les points de montage
attendus par les modules de connexion, courses et documents. Aucun droit ne dépend
de cette présentation : les règles Supabase restent inchangées.
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'accueil': ('index.html', '13 URGENT — Transport express entre professionnels', None),
    'fonctionnement': ('fonctionnement.html', 'Comment fonctionne 13 URGENT ?', 'fonctionnement'),
    'courses': ('courses.html', 'Courses disponibles — 13 URGENT', 'courses'),
    'suivi': ('mes-courses.html', 'Mes courses et leur suivi — 13 URGENT', 'suivi'),
    'deposer': ('deposer.html', 'Déposer une course — 13 URGENT', 'deposer'),
    'tarifs': ('donneurs-ordre.html', 'Donneurs d’ordre — 13 URGENT', 'tarifs'),
    'abonnement-transporteur': ('transporteurs.html', 'Transporteurs et abonnements — 13 URGENT', 'abonnement-transporteur'),
    'espace': ('mon-espace.html', 'Mon espace professionnel — 13 URGENT', 'espace-professionnel'),
}
DESCRIPTIONS = {
    'fonctionnement': 'Découvrez comment déposer une demande de transport et consulter les propositions sur 13 URGENT.',
    'courses': 'Consultez les courses disponibles et envoyez vos propositions confidentielles depuis votre compte transporteur professionnel.',
    'suivi': 'Retrouvez vos courses, leurs propositions et les étapes de chargement et de livraison dans votre espace privé 13 URGENT.',
    'deposer': 'Déposez gratuitement votre demande de transport express entre professionnels sur 13 URGENT.',
    'tarifs': 'Découvrez les conditions de dépôt et les frais de mise en relation pour les donneurs d’ordre professionnels.',
    'abonnement-transporteur': 'Découvrez les étapes d’inscription et les conditions d’accès des transporteurs professionnels à 13 URGENT.',
    'espace': 'Accédez à votre compte professionnel, vos justificatifs, vos abonnements et vos frais 13 URGENT.',
}

def navigation(page, current=None):
    for section, (name, _, _) in PAGES.items():
        page = page.replace('href="#'+section+'"', 'href="'+name+'" data-section-link="'+section+'"')
    # Le menu est commun, avec de vrais liens utilisables sans JavaScript.
    items = [('accueil','Accueil'),('fonctionnement','Fonctionnement'),('courses','Courses'),('suivi','Mes courses'),('deposer','Déposer une course'),('tarifs','Donneurs d’ordre'),('abonnement-transporteur','Transporteurs'),('espace','Mon espace')]
    links = ''.join('<a href="'+PAGES[key][0]+'" data-section-link="'+key+'"'+(' aria-current="page"' if current==key else '')+'>'+label+'</a>' for key,label in items)
    menu = '<button type="button" class="site-menu-toggle btn secondary" aria-expanded="false" aria-controls="siteNavigation">Menu</button><nav id="siteNavigation" aria-label="Navigation principale">'+links+'</nav>'
    page, count = re.subn(r'<nav>.*?</nav>', lambda _:menu, page, count=1)
    if count != 1:
        raise ValueError('Menu principal introuvable')
    page = page.replace('</head>','<link rel="stylesheet" href="site-pages.css?v=20261029-pages"><script src="site-navigation.js?v=20261029-pages" defer></script></head>',1)
    page = page.replace('</body>', '<noscript><style>@media(max-width:800px){.top #siteNavigation{display:grid;grid-template-columns:1fr 1fr}.top .site-menu-toggle{display:none}}</style></noscript></body>',1)
    return page

SPACE = '<section class="section panel" id="espace-professionnel"><div class="section-head left"><span class="eyebrow dark">ESPACE PROFESSIONNEL</span><h1>Mon espace professionnel</h1><p>Retrouvez vos informations, vos justificatifs et vos conditions d’accès.</p></div><div class="actions"><button class="btn primary" type="button" data-account-action="account">Ouvrir mon compte</button><button class="btn secondary" type="button" data-account-action="documents">Mes justificatifs</button><a class="btn secondary" href="mes-courses.html">Mes courses et leur suivi</a></div><p id="spaceNotice" role="status"></p></section>'

def build_pages():
    template=(ROOT/'tools/site-template.html').read_text()
    pages={}
    for key,(filename,title,section) in PAGES.items():
        page=template.replace('<body>','<body data-site-page="'+key+'">',1)
        page=navigation(page,key)
        page=re.sub(r'<title>.*?</title>',lambda _: '<title>'+title+'</title>',page,count=1)
        url='https://13urgent.fr/'+('' if key=='accueil' else filename)
        page=page.replace('rel="canonical" href="https://13urgent.fr/"','rel="canonical" href="'+url+'"')
        page=page.replace('property="og:url" content="https://13urgent.fr/"','property="og:url" content="'+url+'"')
        page=re.sub(r'<meta property="og:title" content="[^"]*">',lambda _:'<meta property="og:title" content="'+title+'">',page,count=1)
        if key in DESCRIPTIONS:
            for prefix in ['name="description"','property="og:description"']:
                page=re.sub('<meta '+prefix+' content="[^"]*">',lambda _,prefix=prefix:'<meta '+prefix+' content="'+DESCRIPTIONS[key]+'">',page,count=1)
        if key in ('suivi','espace'):
            page=page.replace('name="robots" content="index,follow"','name="robots" content="noindex,follow"')
        if section and key!='espace':
            start=page.index('id="'+section+'"')
            a=page.index('<h2>',start);b=page.index('</h2>',a)
            page=page[:a]+page[a:b+5].replace('<h2>','<h1>',1).replace('</h2>','</h1>',1)+page[b+5:]
        if key in ('courses','suivi','deposer'):
            start=page.index('id="'+section+'"')
            end=page.index('</div>',start)+6
            page=page[:end]+'<p class="page-help"><a href="mon-espace.html">Mon compte, mes justificatifs et mes conditions d’accès →</a></p>'+page[end:]
        if key=='espace':
            page=page.replace('</main>',SPACE+'</main>',1)
        pages[filename]=page
    return pages

if __name__=='__main__':
    for name,page in build_pages().items():
        (ROOT/name).write_text(page)

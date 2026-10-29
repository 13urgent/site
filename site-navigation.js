'use strict';
(()=>{
 const pages={accueil:'index.html',fonctionnement:'fonctionnement.html',courses:'courses.html',suivi:'mes-courses.html',deposer:'deposer.html',tarifs:'donneurs-ordre.html','abonnement-transporteur':'transporteurs.html',espace:'mon-espace.html'};
 const sitePage=document.body.dataset.sitePage;
 window.urgentNavigateSection=section=>{
  const key=String(section).replace(/^#/,'');
  if(!pages[key])return false;
  if(document.body.dataset.mobileApp==='true'){
   const views={suivi:'missions',courses:'courses',deposer:'publish',tarifs:'plans','abonnement-transporteur':'plans',espace:'plans'};
   if(views[key]){location.hash=views[key];return true;}return false;
  }
  location.assign(new URL(pages[key],location.href).href);return true;
 };
 const toggle=document.querySelector('.site-menu-toggle'),nav=document.getElementById('siteNavigation');
 if(toggle&&nav){
  function close(){toggle.setAttribute('aria-expanded','false');nav.classList.remove('is-open');}
  toggle.onclick=()=>{const opened=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(opened));nav.classList.toggle('is-open',opened);};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&toggle.getAttribute('aria-expanded')==='true'){close();toggle.focus();}});
  document.addEventListener('click',e=>{if(!nav.contains(e.target)&&!toggle.contains(e.target))close();});
 }
 // Compatibilité des favoris / liens publiés avant la séparation des rubriques.
 function legacy(){
  if(!sitePage)return;
  const key=location.hash.slice(1);if(!pages[key]||key===sitePage)return;
  const q=new URLSearchParams(location.search);if(q.has('code')||q.has('error')||q.has('error_code'))return;
  const target=new URL(pages[key],location.href);target.search=location.search;location.replace(target.href);
 }
 window.addEventListener('hashchange',legacy);legacy();
 for(const b of document.querySelectorAll('[data-account-action]'))b.onclick=async()=>{
  if(b.dataset.accountAction==='account'){document.getElementById('openAccount')?.click();return;}
  const feedback=document.getElementById('spaceNotice');b.disabled=true;
  try{await window.refreshProfessionalAccess?.();const docs=document.getElementById('openDocuments');if(docs&&!docs.hidden){docs.click();feedback.textContent='';}else{feedback.textContent='Connectez-vous avec votre compte professionnel pour accéder à vos justificatifs.';document.getElementById('openAccount')?.click();}}catch{feedback.textContent='Accès aux justificatifs non confirmé. Réessayez avec une connexion internet.';}finally{b.disabled=false;}
 };
})();

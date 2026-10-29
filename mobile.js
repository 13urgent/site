'use strict';
(()=>{
 if(document.body.dataset.mobileApp!=='true')return;
 const offline=document.getElementById('mobileOffline'),status=document.getElementById('mobileStatus');
 function view(name){
  if(!['missions','courses','publish','plans'].includes(name))name='missions';
  document.body.dataset.mobileView=name;
  for(const b of document.querySelectorAll('[data-mobile-view-button]')){if(b.dataset.mobileViewButton===name)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
  history.replaceState(null,'','#'+name);
 }
 for(const b of document.querySelectorAll('[data-mobile-view-button]'))b.onclick=()=>{view(b.dataset.mobileViewButton);window.scrollTo({top:0,behavior:'smooth'});};
 document.getElementById('mobileAccount').onclick=()=>document.getElementById('openAccount').click();
 document.getElementById('mobileDocuments').onclick=async()=>{
  try{await window.refreshProfessionalAccess?.();const b=document.getElementById('openDocuments');if(b.hidden){status.textContent='Connectez-vous avec votre compte professionnel. Si votre espace documentaire n’est pas disponible, contactez l’administration.';document.getElementById('openAccount').click();}else b.click();}catch{status.textContent='Accès aux documents non confirmé. Réessayez avec une connexion internet.';}
 };
 document.getElementById('mobileRefresh').onclick=()=>{if(!navigator.onLine){status.textContent='Reconnectez-vous pour actualiser vos courses.';return;}if(window.urgentMissionFiles?.busy){status.textContent='Un envoi est en cours. Attendez sa fin avant d’actualiser.';return;}window.urgentMarketplaceRefresh?.();};
 function connection(){const wasOffline=!offline.hidden;offline.hidden=navigator.onLine;if(!navigator.onLine)status.textContent='Vous êtes hors connexion. Les changements et fichiers ne seront pas envoyés.';else if(wasOffline)status.textContent='Connexion rétablie. Vous pouvez actualiser vos courses.';}
 window.addEventListener('online',connection);window.addEventListener('offline',connection);connection();
 let installPrompt=null;const install=document.getElementById('mobileInstall');
 window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;install.hidden=false;});
 install.onclick=async()=>{if(!installPrompt)return;await installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;install.hidden=true;};
 window.addEventListener('appinstalled',()=>{install.hidden=true;status.textContent='13 URGENT est installé sur votre téléphone.';});
 if('serviceWorker'in navigator&&window.isSecureContext)navigator.serviceWorker.register('mobile-sw.js').catch(()=>{status.textContent='L’installation hors navigateur n’est pas disponible pour le moment. L’application reste accessible en ligne.';});
 // Le cache conserve les fichiers statiques, jamais les réponses API ou les pièces.
 let updating=false;
 async function sync(){if(updating||document.hidden||!navigator.onLine||window.urgentMissionFiles?.busy||document.querySelector('dialog[open]')||document.body.dataset.mobileView!=='missions'||document.querySelector('.mission-tools details[open],.shipment-edit-form'))return;updating=true;try{await window.urgentMarketplaceRefresh?.();}finally{updating=false;}}
 setInterval(sync,45000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
 view(location.hash.slice(1));
})();

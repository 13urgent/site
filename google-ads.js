'use strict';
// Mesure Google Ads facultative ; aucun appel à Google avant un accord distinct.
(()=>{
 if(document.body.dataset.adminPage==='true'||!['/','/index.html'].includes(location.pathname))return;
 const tag='AW-18537989618',target=tag+'/iTMnCKiasaodEPKLzYdF';
 const key='13urgent_ads_consent_v1',dedupKey='13urgent_ads_sent_v1',maxAge=180*86400000;
 const blocked=navigator.globalPrivacyControl===true||navigator.doNotTrack==='1';
 let choice=null,started=false;const sent=new Set();
 try{const old=JSON.parse(localStorage.getItem(key)||'null');if(old&&['accepted','refused'].includes(old.value)&&Number.isFinite(old.at)&&Date.now()-old.at>=0&&Date.now()-old.at<maxAge)choice=old.value;}catch{}
 function allowed(){return choice==='accepted'&&!blocked;}
 function load(){
  if(started||!allowed())return;
  started=true;
  window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
  // Mode de consentement basique : la bibliothèque n'est chargée qu'après accord.
  window.gtag('consent','default',{ad_storage:'denied',analytics_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
  window.gtag('set','ads_data_redaction',true);
  window.gtag('set','url_passthrough',false);
  window.gtag('consent','update',{ad_storage:'granted',ad_user_data:'granted',analytics_storage:'denied',ad_personalization:'denied'});
  window.gtag('js',new Date());
  window.gtag('config',tag,{send_page_view:false,allow_ad_personalization_signals:false,allow_google_signals:false,allow_enhanced_conversions:false,cookie_expires:90*86400,page_location:location.origin+location.pathname,page_referrer:'',page_title:'13 URGENT'});
  const script=document.createElement('script');script.async=true;script.src='https://www.googletagmanager.com/gtag/js?id='+tag;document.head.append(script);
 }
 function clearCookies(){
  for(const item of document.cookie.split(';')){
   const name=item.split('=')[0].trim();if(!name.startsWith('_gcl_'))continue;
   for(const domain of ['',location.hostname,'.'+location.hostname])document.cookie=name+'=; Max-Age=0; Path=/; SameSite=Lax'+(domain?'; Domain='+domain:'');
  }
 }
 function choose(value){
  const reload=started&&value==='refused';choice=value;
  try{localStorage.setItem(key,JSON.stringify({value,at:Date.now()}));if(value==='refused')localStorage.removeItem(dedupKey);}catch{}
  region.hidden=true;
  if(value==='refused'){sent.clear();clearCookies();if(reload)location.reload();}else load();
 }
 const region=document.createElement('section');region.id='adsChoice';region.className='ads-choice';region.setAttribute('aria-label','Mesure publicitaire facultative');
 const title=document.createElement('strong');title.textContent='Mesure publicitaire facultative';
 const text=document.createElement('p');text.textContent='Autorisez-vous Google Ads à utiliser des cookies pour mesurer les demandes de transport issues de nos annonces ? Google reçoit des données techniques, des identifiants publicitaires et une référence aléatoire de demande, sans son contenu ni vos coordonnées. La personnalisation publicitaire reste désactivée. Votre choix, indépendant des statistiques du site, est conservé 180 jours. Refuser ne bloque pas le service.';
 const link=document.createElement('a');link.href='confidentialite.html#publicite';link.textContent='En savoir plus';
 const actions=document.createElement('div');actions.className='audience-actions';
 function button(label,action){const b=document.createElement('button');b.type='button';b.className='btn secondary';b.textContent=label;b.addEventListener('click',action);actions.append(b);return b;}
 const accept=button('Accepter la mesure publicitaire',()=>choose('accepted'));
 const refuse=button('Refuser la mesure publicitaire',()=>choose('refused'));
 button('Fermer',()=>{region.hidden=true;});
 region.append(title,text,link,actions);
 const footer=document.querySelector('footer');if(!footer)return;
 footer.before(region);
 const settings=document.createElement('button');settings.type='button';settings.className='audience-settings';settings.textContent='Gérer la mesure publicitaire';
 settings.addEventListener('click',()=>{refuse.textContent=started?'Retirer mon accord et recharger':'Refuser la mesure publicitaire';region.hidden=false;region.scrollIntoView({block:'center'});accept.focus();});footer.append(settings);
 if(blocked){accept.disabled=true;text.textContent='La mesure publicitaire est désactivée par le signal de confidentialité de votre navigateur. Le service reste utilisable.';clearCookies();}
 region.hidden=choice!==null||blocked;
 // Ne jamais mémoriser une publication antérieure à l'accord, ni envoyer le formulaire.
 window.urgentAds=Object.freeze({published({id,isTest,role}={}){
  try{
   if(!allowed()||isTest!==false||!['client','carrier'].includes(role)||typeof id!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)||sent.has(id))return;
   let history=[];try{const saved=JSON.parse(localStorage.getItem(dedupKey)||'[]');if(Array.isArray(saved))history=saved.filter(x=>x&&typeof x.id==='string'&&Number.isFinite(x.at)&&Date.now()-x.at>=0&&Date.now()-x.at<90*86400000);}catch{}
   if(history.some(x=>x.id===id))return;
   load();sent.add(id);
   window.gtag('event','conversion',{send_to:target,value:1.0,currency:'EUR',transaction_id:id,page_location:location.origin+location.pathname,page_referrer:'',page_title:'13 URGENT'});
   try{localStorage.setItem(dedupKey,JSON.stringify([...history,{id,at:Date.now()}].slice(-200)));}catch{}
  }catch{/* La mesure ne doit jamais interrompre la publication. */}
 }});
 if(allowed())load();else{clearCookies();try{localStorage.removeItem(dedupKey);}catch{}}
})();

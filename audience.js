'use strict';
(async()=>{
 if(document.body.dataset.adminPage==='true')return;
 const leaf=location.pathname.split('/').pop()||'index.html';
 const pages=['index.html','mentions-legales.html','confidentialite.html','conditions-professionnelles.html','conditions-professionnelles-v3.html','conditions-professionnelles-v4.html'];
 if(!pages.includes(leaf))return;
 if(!window.URGENT_SUPABASE_URL||!window.URGENT_SUPABASE_PUBLISHABLE_KEY)return;
 try{const ready=await fetch(window.URGENT_SUPABASE_URL+'/rest/v1/rpc/urgent_site_stats_public_status',{method:'POST',headers:{apikey:window.URGENT_SUPABASE_PUBLISHABLE_KEY,'Content-Type':'application/json'},body:'{}',credentials:'omit'});if(!ready.ok||(await ready.json()).enabled!==true)return;}catch{return;}
 const key='13urgent_audience_consent_v1',maxAge=180*86400000;
 let choice=null,sent=false;const seen=new Set();
 try{const old=JSON.parse(localStorage.getItem(key)||'null');if(old&&['accepted','refused'].includes(old.value)&&Number.isFinite(old.at)&&Date.now()-old.at>=0&&Date.now()-old.at<maxAge)choice=old.value;}catch{}
 const blocked=navigator.globalPrivacyControl===true||navigator.doNotTrack==='1';
 const region=document.createElement('section');region.id='audienceChoice';region.className='audience-choice';region.setAttribute('aria-label','Statistiques facultatives');region.hidden=true;
 const title=document.createElement('strong');title.textContent='Statistiques facultatives';
 const text=document.createElement('p');text.textContent='Acceptez-vous la mesure des pages consultées et de leur provenance ? Si vous êtes connecté, votre compte et votre entreprise pourront être associés à ces visites. Refuser ne bloque aucune fonction. Votre choix est conservé 180 jours.';
 const policy=document.createElement('a');policy.href='confidentialite.html';policy.textContent='Confidentialité';
 const buttons=document.createElement('div');buttons.className='audience-actions';
 function button(label,fn){const b=document.createElement('button');b.type='button';b.className='btn secondary';b.textContent=label;b.addEventListener('click',fn);buttons.append(b);return b;}
 const accept=button('Accepter les statistiques',()=>choose('accepted'));button('Refuser les statistiques',()=>choose('refused'));button('Fermer',()=>{region.hidden=true;});
 region.append(title,text,policy,buttons);document.body.append(region);
 const settings=document.createElement('button');settings.type='button';settings.className='audience-settings';settings.textContent='Gérer les statistiques';settings.addEventListener('click',()=>{region.hidden=false;accept.focus();});
 (document.querySelector('footer')||document.querySelector('main')||document.body).append(settings);
 if(blocked){accept.disabled=true;text.textContent='La mesure d’audience est désactivée par le signal de confidentialité de votre navigateur. Vous pouvez utiliser le site normalement.';}
 function choose(value){choice=value;try{localStorage.setItem(key,JSON.stringify({value,at:Date.now()}));}catch{}region.hidden=true;if(value==='accepted')record('page_view');}
 function provenance(){
  const q=new URLSearchParams(location.search),allowed=['direct','google','bing','linkedin','instagram','tiktok','facebook'];
  let source=(q.get('utm_source')||'').toLowerCase();
  if(!allowed.includes(source)){
   source='direct';try{const r=new URL(document.referrer);if(r.origin!==location.origin){source='autre';for(const name of ['linkedin','instagram','tiktok','facebook','bing'])if(r.hostname===name+'.com'||r.hostname.endsWith('.'+name+'.com'))source=name;if(/(^|\.)google\.(com|fr)$/.test(r.hostname))source='google';}}catch{}
  }
  const medium=q.get('utm_medium');const campaign=q.get('utm_campaign');
  return {p_source:source,p_medium:['direct','organic','referral','paid_social','organic_social','email'].includes(medium)?medium:source==='direct'?'direct':['google','bing'].includes(source)?'organic':'referral',p_campaign:['lancement_local','premieres_demandes','linkedin_contacts'].includes(campaign)?campaign:'aucune'};
 }
 async function record(kind){
  if(choice!=='accepted'||blocked||!window.URGENT_SUPABASE_URL||!window.URGENT_SUPABASE_PUBLISHABLE_KEY)return;
  if(kind==='page_view'&&sent)return;
  if(kind==='page_view')sent=true;
  const data={p_page:leaf==='index.html'?'/':'/'+leaf,...provenance(),p_kind:kind,p_consent:true};
  try{
   if(typeof sb!=='undefined'&&sb?.rpc)await sb.rpc('urgent_record_site_event',data);
   else await fetch(window.URGENT_SUPABASE_URL+'/rest/v1/rpc/urgent_record_site_event',{method:'POST',headers:{apikey:window.URGENT_SUPABASE_PUBLISHABLE_KEY,'Content-Type':'application/json'},body:JSON.stringify(data),credentials:'omit',keepalive:true});
  }catch{/* Un échec de mesure n’interrompt jamais le site. */}
 }
 if(typeof sb!=='undefined'&&sb?.auth?.onAuthStateChange)sb.auth.onAuthStateChange((event,session)=>{
  const id=session?.user?.id;if(event==='SIGNED_IN'&&id&&choice==='accepted'&&!seen.has(id)){seen.add(id);setTimeout(()=>record('account_seen'),0);}
 });
 if(choice==='accepted')record('page_view');else if(choice===null&&!blocked)region.hidden=false;
})().catch(()=>{});

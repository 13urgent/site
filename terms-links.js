'use strict';
// Métadonnées contractuelles publiques uniquement : aucun compte ni document privé lu.
(async()=>{
 try{
  if(!window.URGENT_SUPABASE_URL||!window.URGENT_SUPABASE_PUBLISHABLE_KEY)return;
  const response=await fetch(window.URGENT_SUPABASE_URL+'/rest/v1/rpc/urgent_commercial_status',{
   method:'POST',headers:{apikey:window.URGENT_SUPABASE_PUBLISHABLE_KEY,'Content-Type':'application/json'},body:'{}'
  });
  if(!response.ok)return;
  const config=await response.json();
  if(!/^conditions-professionnelles-v\d+\.html$/.test(config.document_url||''))return;
  document.querySelectorAll('a[data-current-terms]').forEach(link=>link.href=config.document_url);
  if(document.body.dataset.termsRedirect==='true')location.replace(new URL(config.document_url,location.href));
 }catch{/* Les liens statiques vers la dernière version connue restent accessibles. */}
})();

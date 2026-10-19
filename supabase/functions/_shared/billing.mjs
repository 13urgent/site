// Fonctions pures/testables. Aucun secret ni objet de paiement n'est journalisé.
export const STRIPE_API_VERSION='2024-06-20';
export const PLANS={bronze:{name:'Drive',amount:1250},silver:{name:'Boost',amount:3333},gold:{name:'Premium',amount:6250}};
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
class BillingError extends Error{constructor(status,message){super(message);this.status=status;}}
const fail=(status,message)=>{throw new BillingError(status,message);};
function config(env){
 if(env.BILLING_TEST_ENABLED!=='true')fail(503,'Les paiements de test sont désactivés.');
 if(!env.STRIPE_TEST_SECRET_KEY?.startsWith('sk_test_'))fail(503,'Une clé Stripe de test est requise.');
 if(!env.SUPABASE_URL||!env.SUPABASE_ANON_KEY||!env.SUPABASE_SERVICE_ROLE_KEY)fail(503,'Configuration serveur incomplète.');
 let site;try{site=new URL(env.PUBLIC_SITE_URL);}catch{fail(503,'Adresse du site non configurée.');}
 if(site.username||site.password||site.search||site.hash||(site.protocol!=='https:'&&!(site.protocol==='http:'&&['localhost','127.0.0.1'].includes(site.hostname))))fail(503,'Adresse du site non autorisée.');
 if(!site.pathname.endsWith('/'))site.pathname+='/';
 return{site};
}
function json(status,data,headers={}){return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store',...headers}});}
function cors(req,site){const origin=req.headers.get('Origin');if(origin&&origin!==site.origin)fail(403,'Origine non autorisée.');return{'Access-Control-Allow-Origin':site.origin,'Vary':'Origin','Access-Control-Allow-Headers':'authorization, apikey, content-type, x-client-info','Access-Control-Allow-Methods':'POST, OPTIONS'};}
async function payload(req){
 const reader=req.body?.getReader();if(!reader)return new Uint8Array();const chunks=[];let length=0;
 while(true){const item=await reader.read();if(item.done)break;length+=item.value.length;if(length>1024*1024){await reader.cancel();fail(413,'Requête trop volumineuse.');}chunks.push(item.value);}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return bytes;
}
function services(env,fetcher){
 const supabase=async(path,{token,service=false,method='GET',body}={})=>{
  const key=service?env.SUPABASE_SERVICE_ROLE_KEY:env.SUPABASE_ANON_KEY;
  const response=await fetcher(env.SUPABASE_URL.replace(/\/$/,'')+path,{method,headers:{apikey:key,Authorization:'Bearer '+(token||key),'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
  if(!response.ok)fail(response.status===401?401:409,'Opération refusée par le serveur de données.');
  return response.status===204?null:response.json();
 };
 const stripe=async(path,{method='GET',body,idempotency}={})=>{
  const response=await fetcher('https://api.stripe.com/v1/'+path,{method,headers:{Authorization:'Bearer '+env.STRIPE_TEST_SECRET_KEY,'Stripe-Version':STRIPE_API_VERSION,...(body?{'Content-Type':'application/x-www-form-urlencoded'}:{}),...(idempotency?{'Idempotency-Key':idempotency}:{})},...(body?{body:new URLSearchParams(body).toString()}:{})});
  if(!response.ok)fail(502,'Le prestataire de paiement n’a pas confirmé l’opération.');
  const data=await response.json();if(data.livemode!==false)fail(409,'Objet Stripe hors mode test refusé.');return data;
 };
 const getOrder=async id=>{if(!UUID.test(id||''))fail(400,'Commande incorrecte.');const rows=await supabase('/rest/v1/urgent_billing_orders?id=eq.'+id+'&select=*',{service:true});if(rows.length!==1)fail(409,'Commande introuvable.');return rows[0];};
 return{supabase,stripe,getOrder};
}
function checkPrice(price,plan){const expected=PLANS[plan];if(!expected||!price.active||price.currency!=='eur'||price.unit_amount!==expected.amount||price.recurring?.interval!=='month'||price.recurring?.interval_count!==1||price.tax_behavior!=='exclusive')fail(409,'Le tarif Stripe ne correspond pas au forfait HT mensuel attendu.');}
export async function checkoutHandler(req,env,fetcher=fetch,now=()=>Date.now()){
 let headers={};try{
  const{site}=config(env);headers=cors(req,site);if(req.method==='OPTIONS')return new Response(null,{status:204,headers});if(req.method!=='POST')fail(405,'Méthode non autorisée.');
  const token=req.headers.get('Authorization')?.match(/^Bearer (.+)$/)?.[1];if(!token)fail(401,'Connexion requise.');
  let input;try{input=JSON.parse(new TextDecoder().decode(await payload(req)));}catch(e){if(e instanceof BillingError)throw e;fail(400,'Requête JSON invalide.');}
  if(!input||typeof input!=='object'||Array.isArray(input))fail(400,'Demande incorrecte.');
  if(!UUID.test(input.requestKey||'')||!['subscription','introduction'].includes(input.kind))fail(400,'Demande incorrecte.');
  const service=services(env,fetcher);const user=await service.supabase('/auth/v1/user',{token});if(!user.id||!user.email||!user.email_confirmed_at)fail(401,'Compte confirmé requis.');
  const orders=await service.supabase('/rest/v1/rpc/urgent_billing_create_order',{token,method:'POST',body:{p_request:input.requestKey,p_kind:input.kind,p_plan:input.kind==='subscription'?input.plan:null,p_offer:input.kind==='introduction'?input.offerId:null,p_terms_version:input.termsVersion}});
  const order=orders[0];if(!order||order.user_id!==user.id||!['created','checkout_created'].includes(order.status))fail(409,'Commande non disponible pour paiement.');
  if(order.stripe_session_id){const session=await service.stripe('checkout/sessions/'+encodeURIComponent(order.stripe_session_id));if(session.status!=='open'||session.metadata?.order_id!==order.id||!session.url?.startsWith('https://checkout.stripe.com/'))fail(409,'Session non disponible.');return json(200,{url:session.url,orderId:order.id,test:true},headers);}
  if(new Date(order.expires_at).getTime()-now()<31*60*1000)fail(409,'Cette demande de test a expiré. Créez une nouvelle demande.');
  const params={mode:order.kind==='subscription'?'subscription':'payment',client_reference_id:order.id,customer_email:user.email,'metadata[order_id]':order.id,'line_items[0][quantity]':'1','automatic_tax[enabled]':'true','tax_id_collection[enabled]':'true',billing_address_collection:'required',expires_at:String(Math.floor(new Date(order.expires_at).getTime()/1000)),success_url:new URL('?billing=success&order='+order.id,site).href,cancel_url:new URL('?billing=cancel&order='+order.id,site).href,'payment_method_types[0]':'card'};
  if(order.kind==='subscription'){
   const priceId=env['STRIPE_TEST_PRICE_'+order.plan?.toUpperCase()];if(!/^price_[A-Za-z0-9]+$/.test(priceId||''))fail(503,'Tarif Stripe de test non configuré.');
   const price=await service.stripe('prices/'+priceId);checkPrice(price,order.plan);params['line_items[0][price]']=priceId;params['subscription_data[metadata][order_id]']=order.id;
  }else{params['line_items[0][price_data][currency]']='eur';params['line_items[0][price_data][unit_amount]']=String(order.amount_ht_cents);params['line_items[0][price_data][tax_behavior]']='exclusive';params['line_items[0][price_data][product_data][name]']='13 URGENT — frais de mise en relation (TEST)';}
  const session=await service.stripe('checkout/sessions',{method:'POST',body:params,idempotency:'13urgent-test-'+order.id});
  if(!/^cs_test_[A-Za-z0-9]+$/.test(session.id||'')||session.metadata?.order_id!==order.id||!session.url?.startsWith('https://checkout.stripe.com/'))fail(409,'Session de paiement non conforme.');
  await service.supabase('/rest/v1/rpc/urgent_billing_link_session',{service:true,method:'POST',body:{p_order:order.id,p_session:session.id}});
  return json(200,{url:session.url,orderId:order.id,test:true},headers);
 }catch(e){return json(e.status||500,{error:e instanceof BillingError?e.message:'Opération non confirmée. Aucun paiement réel activé.'},headers);}
}
export async function verifySignature(bytes,header,secret,now=Date.now(),cryptoProvider=globalThis.crypto){
 if(!secret?.startsWith('whsec_')||!header||header.length>4096)return false;
 const values=header.split(',').map(x=>x.split('='));const timestamps=values.filter(([k])=>k==='t');if(timestamps.length!==1||!/^\d+$/.test(timestamps[0][1]))return false;
 const timestamp=Number(timestamps[0][1]);if(!Number.isSafeInteger(timestamp)||Math.abs(Math.floor(now/1000)-timestamp)>300)return false;
 const signatures=values.filter(([k,v])=>k==='v1'&&/^[0-9a-f]{64}$/i.test(v||'')).map(([,v])=>Uint8Array.from(v.match(/../g),h=>parseInt(h,16)));if(!signatures.length)return false;
 const prefix=new TextEncoder().encode(timestamp+'.');const message=new Uint8Array(prefix.length+bytes.length);message.set(prefix);message.set(bytes,prefix.length);
 const key=await cryptoProvider.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['verify']);
 for(const signature of signatures)if(await cryptoProvider.subtle.verify('HMAC',key,signature,message))return true;
 return false;
}
export async function webhookHandler(req,env,fetcher=fetch,now=()=>Date.now()){
 try{
  config(env);if(req.method!=='POST')fail(405,'Méthode non autorisée.');const bytes=await payload(req);
  if(!await verifySignature(bytes,req.headers.get('Stripe-Signature'),env.STRIPE_TEST_WEBHOOK_SECRET,now()))fail(400,'Signature de paiement invalide.');
  let event;try{event=JSON.parse(new TextDecoder().decode(bytes));}catch{fail(400,'Événement invalide.');}
  if(event.livemode!==false||event.api_version!==STRIPE_API_VERSION||!/^evt_[A-Za-z0-9]+$/.test(event.id||'')||!Number.isSafeInteger(event.created)||event.created<0)fail(400,'Événement hors mode test ou version non configurée.');
  const checkoutTypes=['checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.expired'];const subscriptionTypes=['customer.subscription.updated','customer.subscription.deleted','invoice.paid','invoice.payment_failed'];
  if(!checkoutTypes.includes(event.type)&&!subscriptionTypes.includes(event.type))return json(200,{ignored:true});
  const service=services(env,fetcher);let order,session=null,subscription=null,outcome='subscription_sync';
  if(checkoutTypes.includes(event.type)){
   const id=event.data?.object?.id;if(!/^cs_test_[A-Za-z0-9]+$/.test(id||''))fail(400,'Session de test incorrecte.');
   session=await service.stripe('checkout/sessions/'+id);order=await service.getOrder(session.metadata?.order_id);
   if(session.client_reference_id!==order.id||session.mode!==(order.kind==='subscription'?'subscription':'payment'))fail(409,'Session non rattachée à cette commande.');
   if(event.type==='checkout.session.expired'){if(session.status!=='expired')return json(200,{ignored:true});outcome='expired';}
   else{if(session.payment_status!=='paid'||session.status!=='complete')return json(200,{pending:true});outcome='paid_test';if(session.amount_subtotal!==order.amount_ht_cents||session.currency!=='eur')fail(409,'Montant ou devise incorrect.');}
   if(session.subscription)subscription=await service.stripe('subscriptions/'+encodeURIComponent(session.subscription));
  }else{
   let id=event.data?.object?.id;
   if(event.type.startsWith('invoice.')){if(!/^in_[A-Za-z0-9]+$/.test(id||''))fail(400,'Facture incorrecte.');const invoice=await service.stripe('invoices/'+id);if(event.type==='invoice.paid'&&invoice.paid!==true)return json(200,{pending:true});id=invoice.subscription;}
   if(!/^sub_[A-Za-z0-9]+$/.test(id||''))fail(400,'Abonnement incorrect.');subscription=await service.stripe('subscriptions/'+id);order=await service.getOrder(subscription.metadata?.order_id);
  }
  if(subscription){
   if(order.kind!=='subscription'||subscription.metadata?.order_id!==order.id||subscription.items?.data?.length!==1)fail(409,'Abonnement différent de la commande.');
   const item=subscription.items.data[0];if(item.quantity!==1)fail(409,'Quantité incorrecte.');checkPrice({...item.price,active:true},order.plan);
   if(item.price.id!==env['STRIPE_TEST_PRICE_'+order.plan.toUpperCase()])fail(409,'Tarif d’abonnement incorrect.');
  }
  const result=await service.supabase('/rest/v1/rpc/urgent_billing_apply_event',{service:true,method:'POST',body:{p_event:event.id,p_type:event.type,p_created:event.created,p_order:order.id,p_session:session?.id||order.stripe_session_id||null,p_amount:outcome==='paid_test'?session.amount_subtotal:null,p_currency:outcome==='paid_test'?session.currency:null,p_outcome:outcome,p_subscription:subscription?.id||null,p_subscription_status:subscription?.status||null,p_period_end:subscription?.current_period_end?new Date(subscription.current_period_end*1000).toISOString():null}});
  return json(200,{received:true,outcome:result});
 }catch(e){return json(e.status||500,{error:e instanceof BillingError?e.message:'Traitement non confirmé. Réessai serveur nécessaire.'});}
}

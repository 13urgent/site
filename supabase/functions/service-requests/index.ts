// @ts-nocheck
const allowedOrigins=new Set(['https://13urgent.fr','https://www.13urgent.fr','https://13urgent.github.io']);
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function validateQuote(body){
 if(!body||typeof body!=='object'||Array.isArray(body)||!uuid.test(body.id)||body.website)throw Error('invalid_request');
 const text=(key,max,required=true)=>{const v=String(body[key]??'').trim();if(v.length>max||required&&!v||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(v))throw Error('invalid_request');return v;};
 const p={name:text('name',120),email:text('email',254).toLowerCase(),phone:text('phone',30,false),company:text('company',120,false),customer_type:body.customer_type==='business'?'business':'individual',service:text('service',20),origin:text('origin',100),origin_postcode:text('origin_postcode',5),destination:text('destination',100),destination_postcode:text('destination_postcode',5),date:text('date',10),description:text('description',2000),volume_m3:text('volume_m3',10,false),origin_floor:text('origin_floor',3,false),destination_floor:text('destination_floor',3,false),origin_lift:text('origin_lift',12,false),destination_lift:text('destination_lift',12,false),packing:body.packing===true,assembly:body.assembly===true,frequency:text('frequency',20,false),privacy:body.privacy===true};
 if(!/^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$/.test(p.email)||!['express','regular','moving','bulky'].includes(p.service)||!/^\d{5}$/.test(p.origin_postcode)||!/^\d{5}$/.test(p.destination_postcode)||!/^\d{4}-\d{2}-\d{2}$/.test(p.date)||!p.privacy)throw Error('invalid_request');
 const day=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Paris'}).format(new Date());if(p.date<day||!Number.isFinite(Date.parse(p.date+'T12:00:00Z'))||new Date(p.date+'T12:00:00Z').toISOString().slice(0,10)!==p.date)throw Error('invalid_date');
 if(p.volume_m3&&(!/^\d+(?:[.,]\d{1,2})?$/.test(p.volume_m3)||Number(p.volume_m3.replace(',','.'))<=0||Number(p.volume_m3.replace(',','.'))>200))throw Error('invalid_volume');
 for(const f of['origin_floor','destination_floor'])if(p[f]&&!/^(?:[0-9]|1[0-5])$/.test(p[f]))throw Error('invalid_floor');
 for(const f of['origin_lift','destination_lift'])if(p[f]&&!['yes','no','unknown'].includes(p[f]))throw Error('invalid_request');
 if(p.service==='regular'&&!['daily','weekly','monthly','other'].includes(p.frequency))throw Error('invalid_request');return p;
}
const hex=bytes=>Array.from(new Uint8Array(bytes)).map(x=>x.toString(16).padStart(2,'0')).join('');
export async function serviceRequestsHandler(request,env,fetcher=fetch){
 const origin=request.headers.get('origin');const headers={'content-type':'application/json','cache-control':'no-store',...(allowedOrigins.has(origin)?{'access-control-allow-origin':origin,'vary':'Origin','access-control-allow-headers':'content-type,apikey','access-control-allow-methods':'POST,OPTIONS'}:{})};const reply=(status,data)=>new Response(JSON.stringify(data),{status,headers});
 if(origin&&!allowedOrigins.has(origin))return reply(403,{error:'origin_denied'});if(request.method==='OPTIONS')return new Response(null,{status:204,headers});if(request.method!=='POST')return reply(405,{error:'method_not_allowed'});
 if(!env.SUPABASE_URL||!env.SUPABASE_SERVICE_ROLE_KEY||!env.REGISTRATION_ALERTS_SECRET||env.REGISTRATION_ALERTS_SECRET.length<32)return reply(503,{error:'not_configured'});
 let base;try{base=new URL(env.SUPABASE_URL);if(base.protocol!=='https:'||base.pathname!=='/')throw Error();}catch{return reply(503,{error:'not_configured'});}
 try{
  const declared=Number(request.headers.get('content-length')||0);if(declared>24000)return reply(413,{error:'too_large'});const reader=request.body?.getReader();if(!reader)return reply(400,{error:'invalid_request'});let size=0;const chunks=[];for(;;){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>24000){await reader.cancel();return reply(413,{error:'too_large'});}chunks.push(part.value);}const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}let body;try{body=JSON.parse(new TextDecoder().decode(bytes));}catch{return reply(400,{error:'invalid_request'});}
  const rpc=async(name,args)=>{const r=await fetcher(base.origin+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:env.SUPABASE_SERVICE_ROLE_KEY,authorization:'Bearer '+env.SUPABASE_SERVICE_ROLE_KEY,'content-type':'application/json'},body:JSON.stringify(args),signal:AbortSignal.timeout(10000)});return{r,data:await r.json()};};
  if(body.action==='status'){const result=await rpc('urgent_platform_services_policy',{});return reply(200,{enabled:result.r.ok&&result.data?.consumer_quotes===true,area:'France'});}
  if(body.action!=='submit')return reply(400,{error:'invalid_action'});let payload;try{payload=validateQuote(body);}catch(e){return reply(400,{error:e.message});}
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.REGISTRATION_ALERTS_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign']);const digest=async value=>hex(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(value)));
  // L'IP n'est jamais conservée en clair et n'est utilisée que pour limiter les abus.
  const ip=(request.headers.get('x-forwarded-for')||request.headers.get('cf-connecting-ip')||'unknown').split(',')[0].trim();
  const args={p_id:body.id,p_payload:payload,p_hash:hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(payload)))),p_ip_key:await digest('ip/'+ip),p_email_key:await digest('email/'+payload.email)};
  const result=await rpc('urgent_record_quote',args);if(!result.r.ok){if(String(result.data?.message).includes('rate_limit'))return reply(429,{error:'rate_limit'});return reply(502,{error:'save_unconfirmed'});}
  if(result.data!==body.id)return reply(502,{error:'save_unconfirmed'});return reply(200,{saved:true,reference:body.id});
 }catch{return reply(502,{error:'service_unavailable'});}
}
if(typeof Deno!=='undefined')Deno.serve(r=>serviceRequestsHandler(r,Deno.env.toObject()));

'use strict';
const VERSION='13urgent-mobile-20261030-v2';
const FILES=['mobile.html','mobile.css','mobile.js','mobile.webmanifest','assets/mobile-icon.svg','assets/mobile-icon-192.png','assets/mobile-icon-512.png','assets/logo-13urgent-web.png','style.css','config.js','auth.js','app.js','marketplace.js','shipment-schedule.js','mission-files.js','documents.js','manual-commerce.js','billing.js','dossier-organisation.js','document-assistant.js','audience.js','audience.css','google-ads.js','support.js','support.css','support-knowledge.js','terms-links.js'];
const ALLOWED=new Set(FILES.map(p=>new URL(p,self.registration.scope).pathname));
self.addEventListener('install',event=>event.waitUntil(caches.open(VERSION).then(cache=>cache.addAll(FILES))));
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const name of await caches.keys())if(name.startsWith('13urgent-mobile-')&&name!==VERSION)await caches.delete(name);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 // Ne jamais intercepter Auth, Supabase, les fichiers privés, le GPS ou les POST.
 if(req.method!=='GET'||url.origin!==self.location.origin||!ALLOWED.has(url.pathname)||[...url.searchParams.keys()].some(k=>k!=='v'))return;
 event.respondWith((async()=>{
  const cache=await caches.open(VERSION);
  try{const response=await fetch(req);if(response.ok&&response.type!=='opaque')await cache.put(new Request(url.origin+url.pathname),response.clone());return response;}
  catch{const saved=await cache.match(url.origin+url.pathname);return saved||new Response('Connexion internet nécessaire.',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}});}
 })());
});

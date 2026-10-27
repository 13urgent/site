'use strict';
(()=>{
 const kinds=['registration','transport_licence','insurance_rc','insurance_goods'];
 function renewalDate(value){
  const date=new Date(value);if(!value||!Number.isFinite(date.getTime()))return null;
  const p={};for(const part of new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date))p[part.type]=part.value;
  const year=Number(p.year),month=Number(p.month)-1,day=Number(p.day),targetMonth=month+6;
  const end=new Date(Date.UTC(year,targetMonth+1,0)).getUTCDate();return new Date(Date.UTC(year,targetMonth,Math.min(day,end))).toISOString().slice(0,10);
 }
 function today(){const parts={};for(const p of new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()))parts[p.type]=p.value;return parts.year+'-'+parts.month+'-'+parts.day;}
 function latestDocuments(documents){const sorted=[...documents].sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))||String(b.id).localeCompare(String(a.id)));return kinds.map(kind=>sorted.find(d=>d.document_type===kind)).filter(Boolean);}
 function classify(documents){
  const sorted=[...documents].sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))||String(b.id).localeCompare(String(a.id)));
  const latest=kinds.map(kind=>sorted.find(d=>d.document_type===kind));
  if(!documents.length||latest.some(d=>d&&d.review_status!=='approved'))return 'review';
  if(latest.some(d=>!d||!renewalDate(d.created_at)||new Date(d.created_at).getTime()>Date.now()||renewalDate(d.created_at)<=today()||(d.expires_on&&d.expires_on<today())||(d.document_type!=='registration'&&!d.expires_on)))return 'renew';
  return 'validated';
 }
 function folders(host,definitions){
  const containers={};for(const [key,label]of definitions){const details=document.createElement('details');details.className='dossier-folder';details.dataset.folder=key;details.open=key!=='validated';const summary=document.createElement('summary');summary.textContent=label+' (0)';const body=document.createElement('div');body.className='doc-list';details.append(summary,body);host.append(details);containers[key]=body;}
  return {containers,update(){for(const[key,label]of definitions){const body=containers[key];body.parentElement.querySelector('summary').textContent=label+' ('+body.children.length+')';}}};
 }
 window.urgentDossiers=Object.freeze({renewalDate,classify,folders,latestDocuments});
})();

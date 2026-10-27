// Fichiers créés localement : aucun document réel, aucun stockage et aucun réseau métier.
const{chromium}=require('playwright');const fs=require('fs');const assert=require('assert/strict');
(async()=>{const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});try{
 const page=await browser.newPage();let externalRequests=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{
  const url=new URL(route.request().url());if(url.hostname!=='site.example'){externalRequests++;return route.abort();}
  return route.fulfill({contentType:url.pathname==='/document-assistant.js'?'application/javascript':'text/html; charset=utf-8',body:url.pathname==='/document-assistant.js'?fs.readFileSync(__dirname+'/../document-assistant.js','utf8'):'<!doctype html><body><script src="/document-assistant.js"></script>'});
 });
 await page.goto('https://site.example/');
 const cases=await page.evaluate(async()=>{
  const api=window.urgentDocumentAssistant,pdf=()=>new File(['%PDF-1.4\nObjet local de test'], 'immatriculation.pdf',{type:'application/pdf'}),options={kind:'registration',expiry:''};
  const out={};out.missing=await api.inspectFile(null,options);out.empty=await api.inspectFile(new File([],'vide.pdf',{type:'application/pdf'}),options);
  out.large=await api.inspectFile(new File([new Uint8Array(10*1024*1024+1)],'grand.pdf',{type:'application/pdf'}),options);
  out.unsupported=await api.inspectFile(new File(['<svg/>'],'piece.svg',{type:'image/svg+xml'}),options);
  out.inheritedMime=await api.inspectFile(new File(['x'],'piece.pdf',{type:'constructor'}),options);
  out.badKind=await api.inspectFile(pdf(),{kind:'admin',expiry:''});
  out.expiryMissing=await api.inspectFile(pdf(),{kind:'insurance_rc'});out.expiryPast=await api.inspectFile(pdf(),{kind:'transport_licence',expiry:'2000-01-01'});
  out.invalidDate=await api.inspectFile(pdf(),{kind:'insurance_goods',expiry:'2099-02-31'});
  out.badSignature=await api.inspectFile(new File(['<script>bad</script>'],'piece.pdf',{type:'application/pdf'}),options);
  out.mismatch=await api.inspectFile(new File(['%PDF-1.7\n'],'piece.png',{type:'application/pdf'}),options);
  out.dangerousName=await api.inspectFile(new File(['%PDF-1.7\n'],'piece.exe.pdf',{type:'application/pdf'}),options);
  const guarded=pdf();const reads=[];Object.defineProperty(guarded,'slice',{value:function(start,end){reads.push([start,end]);return Blob.prototype.slice.call(this,start,end);}});
  out.pdf=await api.inspectFile(guarded,options);out.reads=reads;
  const canvas=document.createElement('canvas');canvas.width=4;canvas.height=4;canvas.getContext('2d').fillRect(0,0,4,4);
  const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));const jpg=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg'));
  out.png=await api.inspectFile(new File([png],'piece.png',{type:'image/png'}),{kind:'insurance_rc',expiry:'2099-12-31'});
  out.jpg=await api.inspectFile(new File([jpg],'piece.jpeg',{type:'image/jpeg'}),options);
  out.brokenImage=await api.inspectFile(new File([new Uint8Array([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a,0,0,0])],'piece.png',{type:'image/png'}),options);
  out.missingRows=api.analyseChecklist([]);
  const valid=['registration','transport_licence','insurance_rc','insurance_goods'].map(document_type=>({document_type,document_id:'local-'+document_type,review_status:'approved',expires_on:document_type==='registration'?null:'2099-12-31',reason:'valid'}));
  out.validRows=api.analyseChecklist(valid);out.pendingRows=api.analyseChecklist(valid.map(row=>row.document_type==='insurance_rc'?{...row,reason:'not_approved',review_status:'pending'}:row));
  out.expiredRows=api.analyseChecklist(valid.map(row=>row.document_type==='insurance_rc'?{...row,reason:'expired',expires_on:'2000-01-01'}:row));
  out.inconsistentRows=api.analyseChecklist(valid.map(row=>row.document_type==='insurance_rc'?{...row,expires_on:null}:row));
  out.duplicateRows=api.analyseChecklist([...valid,valid[0]]);
  out.unknownRows=api.analyseChecklist(valid.map(row=>row.document_type==='insurance_rc'?{...row,reason:'unexpected'}:row));
  out.approvalUntouched=valid.every(row=>row.review_status==='approved');
  // À 23 h 30 UTC, Paris est déjà au lendemain : éviter une pièce expirée acceptée à minuit.
  const NativeDate=Date;window.Date=class extends NativeDate{constructor(...args){super(...(args.length?args:['2026-10-27T23:30:00Z']));}};
  out.parisExpired=await api.inspectFile(pdf(),{kind:'insurance_rc',expiry:'2026-10-27'});
  out.parisToday=await api.inspectFile(pdf(),{kind:'insurance_rc',expiry:'2026-10-28'});
  return out;
 });
 for(const name of ['missing','empty','large','unsupported','inheritedMime','badKind','expiryMissing','expiryPast','invalidDate','badSignature','mismatch','dangerousName','brokenImage'])assert.equal(cases[name].ok,false,name);
 for(const name of ['pdf','png','jpg']){assert.equal(cases[name].ok,true,name);assert.match(cases[name].message,/ne vaut pas approbation/);}
 assert.deepEqual(cases.reads,[[0,20]]);assert.equal(cases.missingRows.items.length,4);assert.equal(cases.missingRows.ok,false);assert.equal(cases.validRows.ok,true);
 for(const name of ['pendingRows','expiredRows','inconsistentRows','duplicateRows','unknownRows'])assert.equal(cases[name].ok,false,name);
 assert.equal(cases.approvalUntouched,true);assert.equal(externalRequests,0);assert.deepEqual(errors,[]);
  assert.equal(cases.parisExpired.ok,false);assert.equal(cases.parisToday.ok,true);
 console.log('PASS précontrôle documentaire local : taille, vide, MIME/extension/en-tête, image décodable, dates valides, PDF limité à 20 octets ; checklist conservatrice, aucune approbation ni requête externe.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});

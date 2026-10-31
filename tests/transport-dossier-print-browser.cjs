// Synthetic documents only. Requires Playwright, Chromium and pdftotext.
const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('assert/strict');
const {execFileSync}=require('child_process');

const png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg==';
const sample=kind=>({id:'document-synthetique',kind,state:kind==='confirmation'?'issued':'draft',version:3,created_at:'2026-10-31T12:00:00Z',snapshot:{
 shipment_id:'course-synthetique',is_test:true,origin:'Ville de départ',destination:'Ville de livraison',pickup:'2026-11-01T09:00:00Z',delivery_at:'2026-11-01T15:00:00Z',vehicle_type:'Porteur',original_pallets:0,original_weight:0,amount_ht:125,
 owner:{name:'Entreprise fictive A',siret:'00000000000000'},carrier:{name:'Entreprise fictive B',siret:'11111111111111'},
 issuer:{name:'Entreprise fictive émettrice',address:'1 rue fictive\n00000 Ville fictive',contact_email:'exemple@example.com',phone:'0000000000',logo:png},
 data:{order_reference:'ORDRE-FICTIF',customer_reference:'CLIENT-FICTIF',consignor_name:'Expéditeur fictif',consignee_name:'Destinataire fictif',consignor_address:'2 rue fictive, Ville de départ',consignee_address:'3 rue fictive, Ville de livraison',goods_description:'Colis de démonstration',units:0,pallets:0,weight_kg:0,instructions:'Contenu entièrement synthétique.',payment_terms:'Selon accord fictif',vehicle_plate:'AA-000-AA',trailer_plate:'BB-000-BB',driver_name:'Chauffeur fictif',driver_phone:'0000000000',pickup_reservations:'Aucune réserve fictive',delivery_reservations:'Aucune réserve fictive'}
}});

(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 try{
  const page=await browser.newPage();
  await page.setContent('<title>Page privée de départ</title><p>PRIVATE_MAIN_PAGE_SENTINEL</p>');
  await page.evaluate(()=>{
   const profile={id:'acteur-fictif',company_id:'societe-fictive',role:'carrier'};
   window.sb={auth:{getUser:async()=>({data:{user:{id:profile.id}}}),onAuthStateChange:()=>{}},from:()=>({select(){return this},eq(){return this},single:async()=>({data:profile})}),rpc:async name=>({data:name==='urgent_transport_dossier_policy'?{enabled:true}:name==='urgent_transport_document'?window.syntheticDocument:{shipment:{id:'course-synthetique',origin:'Ville de départ',destination:'Ville de livraison'},owner_name:'Entreprise fictive A',carrier_name:'Entreprise fictive B',can_prepare:false,documents:[window.syntheticDocument]}})};
  });
  await page.addScriptTag({content:fs.readFileSync(__dirname+'/../transport-dossier.js','utf8')});
  async function render(row){
   await page.evaluate(value=>{window.syntheticDocument=value;return window.urgentTransportDossier.open(value.snapshot.shipment_id)},row);
   await page.getByRole('button',{name:'Ouvrir / imprimer en PDF',exact:true}).click();
   const frame=page.frameLocator('.dossier-print-frame');
   await frame.getByRole('heading',{name:row.kind==='confirmation'?'Confirmation d’affrètement':'Lettre de voiture',exact:true}).waitFor();
   const source=page.frames().find(f=>f.parentFrame());
   await page.waitForFunction(()=>document.title==='Page privée de départ');
   const html=await source.content();
   assert(!html.includes('PRIVATE_MAIN_PAGE_SENTINEL'));
   assert.equal(await frame.locator('header h2').textContent(),row.kind==='waybill'?'Entreprise fictive émettrice':'Émetteur');
   assert.equal(await frame.locator('header .logo').count(),row.snapshot.issuer.logo?1:0);
   assert.equal(await source.title(),(row.kind==='confirmation'?'Confirmation d’affrètement':'Lettre de voiture')+' — ORDRE-FICTIF — V3');
   if(row.kind==='waybill'){for(const key of['units','pallets','weight_kg'])assert.equal(await frame.locator('[data-paper-quantity='+key+']').textContent(),'0');}else for(const name of ['Nombre d’unités','Palettes déclarées','Poids déclaré (kg)'])assert.equal(await frame.locator('.field').filter({has:frame.locator('dt').filter({hasText:name})}).locator('dd').textContent(),'0');
   const printed=await browser.newPage();
   try{
    await printed.setContent(html);
    const pdf=await printed.pdf({preferCSSPageSize:true,printBackground:true});
    const count=(pdf.toString('latin1').match(/\/Type\s*\/Page\b/g)||[]).length;
    const text=execFileSync('pdftotext',['-','-'],{input:pdf,encoding:'utf8'});
    assert(text.includes('Entreprise fictive émettrice'));
    return {count,text,frame};
   }finally{await printed.close()}
  }
  for(const kind of ['confirmation','waybill']){
   const result=await render(sample(kind));if(kind==='waybill'){assert.equal(await result.frame.locator('.lv-signatures>section').count(),4);assert.equal(await result.frame.locator('.signature-space').count(),4);assert.equal(await result.frame.locator('img.platform-logo[alt="13 URGENT"]').count(),1);assert(result.text.includes('Préparé avec 13 URGENT'));assert(result.text.includes('Chargement'));assert(result.text.includes('Livraison'));assert(result.text.includes('Arrivée réelle'));assert(result.text.includes('Départ réel'));for(const name of['Conducteur — chargement','Expéditeur','Conducteur — livraison','Destinataire'])assert(result.text.includes(name));assert(result.text.includes('Signature et cachet'));}
   assert.equal(result.count,1,kind+' short document must fit one A4 page');
   assert.equal(await result.frame.getByText('Référence e-CMR externe',{exact:true}).count(),0);
  }
  const noBrand=sample('waybill');noBrand.snapshot.issuer={name:'Entreprise fictive émettrice'};
  const missing=await render(noBrand);
  assert.equal(missing.count,1);
  assert((await missing.frame.locator('header').innerText()).includes('À préciser'));
  const withReference=sample('confirmation');withReference.snapshot.data.external_ecmr_reference='REFERENCE-EXTERNE-FICTIVE';
  assert((await render(withReference)).text.includes('REFERENCE-EXTERNE-FICTIVE'));
  const unbroken=sample('waybill');unbroken.snapshot.data.instructions='Z'.repeat(1800)+' FIN_MOT_LONG';
  const wrapped=await render(unbroken);
  assert.equal((wrapped.text.match(/Z/g)||[]).length,1800,'Long unbroken content must wrap without clipping');
  assert(wrapped.text.includes('FIN_MOT_LONG'));
  const multiline=sample('waybill');
  const lineMarkers=Array.from({length:180},(_,index)=>'LIGNE_'+String(index).padStart(3,'0'));
  multiline.snapshot.data.instructions=lineMarkers.join('\n');
  const continued=await render(multiline);
  assert(continued.count>=3,'A single tall field must continue across pages');
  for(const marker of lineMarkers)assert(continued.text.includes(marker),'Multiline content must retain '+marker);
  for(const kind of ['confirmation','waybill']){
   const long=sample(kind),ends=[];
   for(const [key,size]of Object.entries({consignor_address:1000,consignee_address:1000,goods_description:1000,instructions:2000,...(kind==='confirmation'?{payment_terms:1000}:{pickup_reservations:2000,delivery_reservations:2000})})){
    const end='FIN_'+key.toUpperCase();ends.push(end);
    long.snapshot.data[key]=('Texte de démonstration synthétique. '.repeat(100)).slice(0,size-end.length-1)+' '+end;
   }
   const result=await render(long);
   assert(result.count>1,kind+' long document must continue on further pages');
   for(const end of ends)assert(result.text.includes(end),'Printed content must retain '+end);
   assert(result.text.replace(/\s+/g,' ').includes('Les documents signés et photos restent à joindre au dossier de mission.'));
  }
  console.log('PASS transport print: short A4 documents, issuer/header, snapshot branding, zero quantities, references, titles and complete long documents.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});

const fs=require('fs');const assert=require('node:assert/strict');const{createDatabase,uid}=require('./helpers/pilot-database.cjs');
(async()=>{const{db,actor}=await createDatabase({includeBilling:false});try{
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610200001_manual_commerce.sql','utf8'));
 await db.query("update public.carrier_documents set created_at=now()-interval '6 months' where company_id=$1 and document_type='registration'",[uid(3)]);
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610270002_document_renewal.sql','utf8'));
 await actor(3);assert.equal((await db.query('select public.urgent_carrier_ready($1) as ok',[uid(3)])).rows[0].ok,false);
 let rows=(await db.query('select * from public.urgent_document_checklist($1)',[uid(3)])).rows;assert.equal(rows.find(x=>x.document_type==='registration').reason,'renewal_due');
 await assert.rejects(db.query('select * from public.urgent_document_checklist($1)',[uid(4)]));
 await db.exec('reset role');await assert.rejects(db.query('update public.carrier_documents set created_at=now() where company_id=$1',[uid(3)]));
 const inserted=(await db.query("insert into public.carrier_documents(company_id,document_type,review_status,created_at)values($1,'registration','approved',now()+interval '3 years')returning id,created_at<=now() as server_date",[uid(3)])).rows[0];assert.equal(inserted.server_date,true);
 await actor(3);assert.equal((await db.query('select public.urgent_carrier_ready($1) as ok',[uid(3)])).rows[0].ok,true);
 await db.exec('reset role');await db.query("update public.carrier_documents set review_status='pending' where id=$1",[inserted.id]);
 await actor(3);assert.equal((await db.query('select public.urgent_carrier_ready($1) as ok',[uid(3)])).rows[0].ok,false);
 await db.exec('reset role');await db.query("update public.carrier_documents set expires_on=current_date-1 where company_id=$1 and document_type='insurance_rc'",[uid(3)]);
 await actor(3);rows=(await db.query('select * from public.urgent_document_checklist($1)',[uid(3)])).rows;assert.equal(rows.find(x=>x.document_type==='insurance_rc').reason,'expired');
 await db.exec('reset role');assert.equal((await db.query("select to_char(public.urgent_document_renewal_due('2026-08-31T12:00:00Z') at time zone 'Europe/Paris','YYYY-MM-DD')as day")).rows[0].day,'2027-02-28');
 await db.exec('set role anon');assert.equal((await db.query('select public.urgent_document_renewal_policy()as p')).rows[0].p.months,6);await assert.rejects(db.query('select * from public.urgent_document_checklist($1)',[uid(3)]));
}finally{await db.close();}
 const{chromium}=require('playwright');const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});try{const p=await b.newPage();await p.setContent('<main></main>');await p.addScriptTag({content:fs.readFileSync(__dirname+'/../dossier-organisation.js','utf8')});
 const result=await p.evaluate(()=>{const module=window.urgentDossiers,fresh=new Date(Date.now()-86400000).toISOString();const docs=['registration','transport_licence','insurance_rc','insurance_goods'].map((kind,i)=>({id:String(i),document_type:kind,created_at:fresh,expires_on:'2099-01-01',review_status:'approved'}));const good=module.classify(docs);const renew=module.classify(docs.map(d=>({...d,created_at:'2020-01-01T00:00:00Z'})));const pending=module.classify([...docs,{...docs[0],id:'new',created_at:new Date().toISOString(),review_status:'pending'}]);const f=module.folders(document.querySelector('main'),[['review','À examiner'],['validated','Classés']]);f.containers.validated.append(document.createElement('article'));f.update();return {good,renew,pending,date:module.renewalDate('2026-08-31T12:00:00Z'),closed:!f.containers.validated.parentElement.open,count:f.containers.validated.parentElement.querySelector('summary').textContent};});assert.deepEqual(result,{good:'validated',renew:'renew',pending:'review',date:'2027-02-28',closed:true,count:'Classés (1)'});
}finally{await b.close();}
 console.log('PASS dossiers : classement, nouvelles pièces prioritaires, archives repliées, six mois calendaires/fin de mois, renouvellement imposé côté serveur, date dépôt non falsifiable, propriétaire/anon, expiration antérieure et droits commerciaux conservés.');
})().catch(e=>{console.error(e);process.exit(1)});

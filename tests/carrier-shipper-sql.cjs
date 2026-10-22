const{createDatabase}=require('./helpers/pilot-database.cjs');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const{db,uid,actor}=await createDatabase({includeBilling:false});
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610200001_manual_commerce.sql','utf8'));
 const publish=async()=> (await db.query("select public.urgent_publish_shipment('Marseille','Aix',now()+interval '7 days','VL / fourgon',1,300,'Transporteur donneur d’ordre','test@example.com','Instructions privées') id")).rows[0].id;
 await actor(3);await assert.rejects(publish());await db.exec('reset role');
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610220001_carrier_shipper.sql','utf8'));
 // Idempotence de la migration.
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610220001_carrier_shipper.sql','utf8'));
 for(const n of [1,2,3]){await actor(n);assert(await publish());}
 await actor(3);const shipment=await publish();
 await assert.rejects(db.query('select public.urgent_submit_offer($1,450)',[shipment]),/propre entreprise/);
 await assert.rejects(db.query("select public.urgent_publish_test_shipment('TEST','TEST',now()+interval '1 day','VL / fourgon',1,300,'Test','test@example.com','')"),/administration/);
 await actor(4);const offer=(await db.query('select public.urgent_submit_offer($1,450) id',[shipment])).rows[0].id;
 assert.equal((await db.query('select * from public.urgent_shipment_private where shipment_id=$1',[shipment])).rows.length,0);
 await actor(2);await assert.rejects(db.query('select public.urgent_accept_offer($1,true,450)',[offer]));
 await actor(3);await db.query('select public.urgent_accept_offer($1,true,450)',[offer]);
 assert.equal((await db.query('select assigned_company_id from public.urgent_shipments where id=$1',[shipment])).rows[0].assigned_company_id,uid(4));
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.urgent_service_entries')).rows[0].n,0);
 await db.query('update public.urgent_business_access set registry_checked=false where company_id=$1',[uid(3)]);await actor(3);await assert.rejects(publish(),/vérifier/);await db.exec('reset role');await db.query('update public.urgent_business_access set registry_checked=true where company_id=$1',[uid(3)]);
 await actor(1);await db.query("select public.urgent_set_commercial_mode(true,'CHRONOSS - VIREMENTS ET FACTURATION MANUELLE')");
 for(const n of [3,4]){await actor(n);await db.query("select public.urgent_accept_terms('PRO-B2B-2026-10-20-v3')");}
 await actor(1);const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris'}).format(new Date());for(const n of [3,4])await db.query("select public.urgent_record_bank_subscription($1,'bronze',$2,1500,1500,$3,$4,true)",[uid(n),today,'BANK-TEST-'+n,'INV-TEST-'+n]);
 await actor(3);const paid=await publish();await actor(4);const paidOffer=(await db.query('select public.urgent_submit_offer($1,450) id',[paid])).rows[0].id;
 await actor(3);await assert.rejects(db.query("select public.urgent_accept_commercial_offer($1,450,675,'PRO-B2B-2026-10-20-v3',false)",[paidOffer]));await assert.rejects(db.query("select public.urgent_accept_commercial_offer($1,450,1,'PRO-B2B-2026-10-20-v3',true)",[paidOffer]));
 await db.query("select public.urgent_accept_commercial_offer($1,450,675,'PRO-B2B-2026-10-20-v3',true)",[paidOffer]);
 await db.exec('reset role');const fee=(await db.query('select company_id,amount_ht_cents from public.urgent_service_entries where shipment_id=$1',[paid])).rows[0];assert.equal(fee.company_id,uid(3));assert.equal(fee.amount_ht_cents,675);
 await actor(2);assert.equal((await db.query('select * from public.urgent_shipment_private where shipment_id=$1',[paid])).rows.length,0);
 await db.exec('reset role;set role anon');await assert.rejects(publish());
 await db.close();console.log('PASS : publication admin/client/transporteur, vérification établissement, confidentialité, refus auto-offre, sélection par transporteur propriétaire, frais/consentement commercial et refus anonyme');
})().catch(e=>{console.error(e);process.exit(1)});

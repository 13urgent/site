const {createDatabase,uid}=require('./helpers/pilot-database.cjs');const assert=require('assert/strict');const fs=require('fs');
(async()=>{
 const {db,actor}=await createDatabase({includeBilling:false});await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610200001_manual_commerce.sql','utf8'));
 let bankId=0;
 const subscription=(ref,company=3)=>db.query("insert into public.urgent_manual_subscriptions(company_id,plan,starts_at,ends_at,expected_ttc_cents,received_cents,bank_reference,invoice_reference,recorded_by)values($1,'bronze',now(),now()+interval '1 month',1500,1500,$2,$3,$4) returning id",[uid(company),'BANK-'+(++bankId),ref,uid(1)]);
 const registry=(ref,company)=>db.query('insert into public.urgent_external_invoice_registry values($1,$2)',[ref,uid(company)]);
 // Historique incohérent : ni effacement ni échec d'installation. Référence groupée valide aussi.
 await subscription('HISTORY-CONFLICT');await registry('HISTORY-CONFLICT',2);await subscription('HISTORY-SAME');await registry('HISTORY-SAME',3);
 const migration=fs.readFileSync(__dirname+'/../supabase/migrations/202610230005_invoice_reference_boundary.sql','utf8');
 const first=await db.exec(migration);assert.equal(first[0].rows.length,1);assert.equal(first[0].rows[0].reference,'HISTORY-CONFLICT');assert.equal(first.at(-1).rows[0].protection_references_active,true);assert.equal(Number(first.at(-1).rows[0].conflits_historiques_a_examiner),1);
 await db.exec(migration);assert.equal((await db.query('select count(*)::int n from public.urgent_manual_subscriptions')).rows[0].n,2);assert.equal((await db.query('select count(*)::int n from public.urgent_invoice_reference_companies')).rows[0].n,0);
 await registry('HISTORY-SAME',3).catch(e=>assert.match(e.message,/duplicate key/));await assert.rejects(registry('HISTORY-CONFLICT',4),/historique/);
 // Deux sens du rapprochement, même entreprise autorisée, autre entreprise refusée.
 await subscription('BUNDLE-A');await registry('BUNDLE-A',3);await assert.rejects(registry('BUNDLE-A',2),/autre entreprise/);
 await registry('BUNDLE-B',3);await subscription('BUNDLE-B');await assert.rejects(subscription('BUNDLE-B',4),/autre entreprise/);
 // Annulation transactionnelle de la réservation : aucune référence fantôme à la suite d'une erreur.
 await db.exec('begin');await registry('ROLLBACK-TEST',2);await db.exec('rollback');await subscription('ROLLBACK-TEST',3);
 const shipment=(await db.query("insert into public.urgent_shipments(owner_id,owner_company_id,origin,destination,pickup,vehicle,pallets,weight)values($1,$1,'Marseille','Aix',now()+interval '1 day','VL / fourgon',1,100) returning id",[uid(2)])).rows[0].id;
 const offer=(await db.query('insert into public.urgent_offers(shipment_id,carrier_id,carrier_company_id,amount_ht)values($1,$2,$2,500) returning id',[shipment,uid(3)])).rows[0].id;
 const fee=(await db.query("insert into public.urgent_service_entries(request_key,company_id,shipment_id,offer_id,kind,transport_ht,amount_ht_cents,reason,terms_version,created_by)values(gen_random_uuid(),$1,$2,$3,'fee',500,750,'Test','v3',$1) returning id",[uid(2),shipment,offer])).rows[0].id;
 await actor(1);await assert.rejects(db.query('select public.urgent_mark_external_invoice($1,$2)',[[fee],'BUNDLE-A']),/autre entreprise/);await db.query('select public.urgent_mark_external_invoice($1,$2)',[[fee],'FEE-COMPANY2']);await db.exec('reset role');await assert.rejects(subscription('FEE-COMPANY2',3),/autre entreprise/);
 await assert.rejects(db.query('update public.urgent_service_entries set external_invoice_reference=$1 where id=$2',['BUNDLE-A',fee]),/autre entreprise/);
 await registry('ENTRY-DIRECT',2);await subscription('ENTRY-DIRECT',2);await db.query('update public.urgent_service_entries set external_invoice_reference=$1 where id=$2',['ENTRY-DIRECT',fee]);
 for(const role of ['anon','authenticated','service_role']){await db.exec('set role '+role);await assert.rejects(db.query('select * from public.urgent_invoice_reference_companies'));await assert.rejects(db.query("select public.urgent_enforce_invoice_company()"));await db.exec('reset role');}
 assert.equal((await db.query('select amount_ht_cents from public.urgent_service_entries where id=$1',[fee])).rows[0].amount_ht_cents,750);assert.equal((await db.query('select count(*)::int n from public.urgent_service_entries')).rows[0].n,1);assert.equal((await db.query('select count(*)::int n from public.urgent_manual_subscriptions')).rows[0].n,6);
 await db.close();console.log('PASS références factures : migration réexécutable, historique préservé et signalé, abonnement/frais même entreprise autorisés, conflits interentreprises refusés dans les deux sens, écritures directes couvertes, réservation atomique unique et rollback, accès privé, aucun montant modifié.');
})().catch(e=>{console.error(e);process.exit(1)});

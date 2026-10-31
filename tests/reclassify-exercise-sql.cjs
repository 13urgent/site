const { createDatabase } = require('./helpers/pilot-database.cjs');
const fs = require('fs');
const assert = require('assert/strict');

(async () => {
 const { db, actor, uid } = await createDatabase({ includeBilling: false });
 try {
  await db.exec(`create schema storage;
   create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
   create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,owner_id text,metadata jsonb);
   alter table auth.users add column email_confirmed_at timestamptz;`);
  for (const name of [
   '202610200001_manual_commerce.sql', '202610220001_carrier_shipper.sql',
   '202610230005_invoice_reference_boundary.sql', '202610270002_document_renewal.sql',
   '202610280002_archive_shipments.sql', '202610290002_mobile_missions.sql',
   '202610300001_shipment_schedule.sql', '202610310001_transport_dossier.sql',
   '202610310002_internal_premium.sql', '202610310003_start_reauthorization.sql', '202610310004_reclassify_exercise.sql',
  ]) await db.exec(fs.readFileSync(__dirname + '/../supabase/migrations/' + name, 'utf8'));
  const reason = 'Exercice fictif confirmé avant tout transport réel';
  const terms = 'PRO-B2B-2026-10-20-v3';
  const reclassify = (sid, why = reason, confirm = true) => db.query(
   'select public.urgent_reclassify_exercise($1,$2,$3) result', [sid, why, confirm]
  );
  await actor(1);
  await db.query("select public.urgent_set_commercial_mode(true,'CHRONOSS - VIREMENTS ET FACTURATION MANUELLE')");
  for (const n of [2, 3]) {
   await db.query('select public.urgent_review_transport_document_access($1,true)', [uid(n)]);
  }
  for (const n of [2, 3]) {
   await actor(n);
   await db.query('select public.urgent_accept_terms($1)', [terms]);
  }
  await actor(1);
  const today = (await db.query("select (now()at time zone'Europe/Paris')::date::text d")).rows[0].d;
  await db.query("select public.urgent_record_bank_subscription($1,'gold',$2,7500,7500,'SYNTHETIC-BANK','SYNTHETIC-SUBSCRIPTION',true)", [uid(3), today]);
  const subscriptions = (await db.query('select * from public.urgent_manual_subscriptions order by id')).rows;
  const access = (await db.query('select * from public.urgent_business_access order by company_id')).rows;

  async function course(assigned = true, amount = 450) {
   await actor(2);
   const sid = (await db.query("select public.urgent_publish_shipment('Ville A','Ville B',now()+interval '7 days','Porteur',1,300,'Client fictif','client@example.com','Exercice de recette') id")).rows[0].id;
   if (assigned) {
    await actor(3);
    const oid = (await db.query('select public.urgent_submit_offer($1,$2) id', [sid, amount])).rows[0].id;
    await actor(2);
    await db.query('select public.urgent_accept_commercial_offer($1,$2,$3,$4,true)', [oid, amount, Math.round(amount * 100 * 0.015), terms]);
   }
   await actor(1);
   return sid;
  }
  const entries = async sid => (await db.query('select * from public.urgent_service_entries where shipment_id=$1 order by id', [sid])).rows;
  const shipment = async sid => (await db.query('select * from public.urgent_shipments where id=$1', [sid])).rows[0];

  const sid = await course();
  for (const n of [2, 3, 4]) {
   await actor(n);
   await assert.rejects(reclassify(sid), /Administration/);
  }
  await actor(1);
  for (const confirm of [false, null]) await assert.rejects(reclassify(sid, reason, confirm), /Confirmez/);
  for (const why of [null, 'court', 'x'.repeat(1001)]) await assert.rejects(reclassify(sid, why), /motif/);
  await assert.rejects(reclassify(uid(999)), /introuvable/);
  await assert.rejects(db.query('update public.urgent_shipments set is_test=true where id=$1', [sid]), /permission denied/);
  await assert.rejects(db.query('select * from public.urgent_exercise_reclassifications'), /permission denied/);

  // An issued snapshot is immutable; only a newly saved version sees the test flag.
  const payload = { consignor_name: 'Expéditeur fictif', consignor_address: 'Adresse A',
   consignee_name: 'Destinataire fictif', consignee_address: 'Adresse B',
   goods_description: 'Marchandises fictives', pallets: 1, weight_kg: 300,
   payment_terms: 'Aucun transport réel pour cette recette' };
  await actor(2);
  await db.query('select public.urgent_save_document_branding(0,$1)', [{ address: 'Adresse entreprise fictive' }]);
  await db.query("select public.urgent_save_transport_document($1,$2,'confirmation',0,'issued',$3,true)", [uid(90), sid, payload]);
  const issued = (await db.query('select * from public.urgent_transport_documents where id=$1', [uid(90)])).rows[0];
  assert.equal(issued.snapshot.is_test, false);
  await actor(1);
  const base = (await entries(sid))[0];
  await db.query('select public.urgent_credit_service_fee($1,100,$2,$3)', [base.id, 'Réduction partielle fictive déjà examinée', uid(91)]);
  const beforeEntries = await entries(sid);
  const beforeShipment = await shipment(sid);
  const beforeEvents = (await db.query('select count(*)::int n from public.urgent_shipment_events where shipment_id=$1', [sid])).rows[0].n;
  const result = (await reclassify(sid)).rows[0].result;
  assert.deepEqual(result, { reclassified: true, credited_cents: 575 });
  const afterEntries = await entries(sid);
  assert.equal(afterEntries.length, 3);
  for (const prior of beforeEntries) assert.deepEqual(afterEntries.find(e => e.id === prior.id), prior);
  assert.equal(afterEntries.reduce((sum, e) => sum + e.amount_ht_cents, 0), 0);
  const created = afterEntries.find(e => !beforeEntries.some(prior => prior.id === e.id));
  assert.equal(created.parent_id, base.id);
  assert.equal(created.amount_ht_cents, -575);
  assert.equal(created.reason, reason);
  const afterShipment = await shipment(sid);
  assert.equal(afterShipment.is_test, true);
  for (const key of ['status', 'accepted_offer_id', 'assigned_company_id', 'archived_at']) assert.equal(afterShipment[key], beforeShipment[key]);
  assert.equal((await db.query('select count(*)::int n from public.urgent_shipment_events where shipment_id=$1', [sid])).rows[0].n, beforeEvents + 1);
  await db.exec('reset role');
  const audit = (await db.query("select * from public.urgent_commercial_audit where action='exercise_reclassified' and target_id=$1", [sid])).rows;
  assert.equal(audit.length, 1);
  assert.equal(JSON.parse(audit[0].details).credited_cents, 575);
  assert.deepEqual((await db.query('select * from public.urgent_transport_documents where id=$1', [uid(90)])).rows[0], issued);
  await actor(2);
  await db.query("select public.urgent_save_transport_document($1,$2,'confirmation',1,'issued',$3,true)", [uid(92), sid, payload]);
  assert.equal((await db.query('select snapshot from public.urgent_transport_documents where id=$1', [uid(92)])).rows[0].snapshot.is_test, true);

  // Exact replay is read-only even if operational state or invoicing later changes.
  await actor(1);
  await db.query('select public.urgent_mark_external_invoice($1,$2)', [[created.id], 'SYNTHETIC-EXTERNAL-CREDIT']);
  await db.exec('reset role');
  await db.query("update public.urgent_shipments set status='completed',archived_at=now() where id=$1", [sid]);
  await actor(1);
  assert.deepEqual((await reclassify(sid)).rows[0].result, result);
  assert.equal((await entries(sid)).length, 3);
  await assert.rejects(reclassify(sid, reason + ' modifié'), /décision/);
  await db.exec('reset role');
  assert.equal((await db.query("select count(*)::int n from public.urgent_commercial_audit where action='exercise_reclassified' and target_id=$1", [sid])).rows[0].n, 1);

  // Zero, fully corrected and absent fees need no new financial writing.
  for (const kind of ['no-fee', 'zero-fee', 'fully-credited']) {
   const sample = await course(kind !== 'no-fee', kind === 'zero-fee' ? 0.01 : 450);
   const fee = (await entries(sample))[0];
   if (kind === 'fully-credited') await db.query('select public.urgent_credit_service_fee($1,$2,$3,$4)', [fee.id, fee.amount_ht_cents, 'Correction totale fictive déjà examinée', uid(93)]);
   const count = (await entries(sample)).length;
   assert.deepEqual((await reclassify(sample, 'x'.repeat(1000))).rows[0].result, { reclassified: true, credited_cents: 0 });
   assert.equal((await entries(sample)).length, count);
  }
  const longReason = await course();
  assert.equal((await reclassify(longReason, 'x'.repeat(1000))).rows[0].result.credited_cents, 675);

  // An external reference on either the fee or one of its credits blocks all changes.
  for (const billedKind of ['fee', 'credit']) {
   const sample = await course();
   const fee = (await entries(sample))[0];
   let billedId = fee.id;
   if (billedKind === 'credit') billedId = (await db.query('select public.urgent_credit_service_fee($1,100,$2,$3) id', [fee.id, 'Correction partielle fictive pour facture', uid(94)])).rows[0].id;
   await db.query('select public.urgent_mark_external_invoice($1,$2)', [[billedId], 'SYNTHETIC-INVOICE-' + billedKind]);
   const original = await entries(sample);
   await assert.rejects(reclassify(sample), /facture externe.*avoir externe/);
   assert.equal((await shipment(sample)).is_test, false);
   assert.deepEqual(await entries(sample), original);
  }

  // Only pre-loading, unarchived operational states may be reclassified.
  for (const status of ['heading_pickup', 'at_pickup', 'loaded', 'delivery_reported', 'completed', 'cancelled']) {
   const sample = await course(false);
   await db.exec('reset role');
   await db.query('update public.urgent_shipments set status=$1 where id=$2', [status, sample]);
   await actor(1);
   if (['heading_pickup', 'at_pickup'].includes(status)) assert.equal((await reclassify(sample)).rows[0].result.reclassified, true);
   else {
    await assert.rejects(reclassify(sample), /avant chargement/);
    assert.equal((await shipment(sample)).is_test, false);
   }
  }
  const archived = await course(false);
  await db.exec('reset role');
  await db.query('update public.urgent_shipments set archived_at=now() where id=$1', [archived]);
  await actor(1);
  await assert.rejects(reclassify(archived), /archivée/);
  const existingTest = await course(false);
  await db.exec('reset role');
  await db.query('update public.urgent_shipments set is_test=true where id=$1', [existingTest]);
  await actor(1);
  await assert.rejects(reclassify(existingTest), /déjà un exercice/);

  // A deliberate request-key collision after a first correction rolls everything back.
  const atomic = await course();
  const first = (await entries(atomic))[0];
  await db.exec('reset role');
  await db.query('update public.urgent_service_entries set id=$1 where id=$2', [uid(601), first.id]);
  await db.query("insert into public.urgent_offers(id,shipment_id,carrier_id,carrier_company_id,amount_ht,status)values($1,$2,$3,$3,100,'not_selected')", [uid(602), atomic, uid(4)]);
  await db.query("insert into public.urgent_service_entries(id,request_key,company_id,shipment_id,offer_id,kind,transport_ht,amount_ht_cents,reason,terms_version,created_by)values($1,$2,$3,$4,$2,'fee',100,150,'Frais fictifs additionnels',$5,$6)", [uid(603), uid(602), uid(2), atomic, terms, uid(1)]);
  const conflict = (await db.query("select md5('urgent-exercise-reclassification/'||$1::uuid::text)::uuid id", [uid(603)])).rows[0].id;
  await actor(1);
  await db.query('select public.urgent_credit_service_fee($1,1,$2,$3)', [uid(601), 'Autre correction avec référence occupée', conflict]);
  const original = await entries(atomic);
  await assert.rejects(reclassify(atomic), /Identifiant de correction déjà utilisé/);
  assert.equal((await shipment(atomic)).is_test, false);
  assert.deepEqual(await entries(atomic), original);
  await db.exec('reset role');
  assert.equal((await db.query('select count(*)::int n from public.urgent_exercise_reclassifications where shipment_id=$1', [atomic])).rows[0].n, 0);
  assert.equal((await db.query("select count(*)::int n from public.urgent_shipment_events where shipment_id=$1 and event_type='reclassified_as_exercise'", [atomic])).rows[0].n, 0);
  // Releasing the synthetic collision allows both fee balances to be compensated.
  await db.query('update public.urgent_service_entries set request_key=$1 where request_key=$2', [uid(604), conflict]);
  await actor(1);
  assert.deepEqual((await reclassify(atomic)).rows[0].result, { reclassified: true, credited_cents: 824 });
  assert.equal((await entries(atomic)).reduce((sum, e) => sum + e.amount_ht_cents, 0), 0);
  await db.exec('reset role');
  assert.deepEqual((await db.query('select * from public.urgent_manual_subscriptions order by id')).rows, subscriptions);
  assert.deepEqual((await db.query('select * from public.urgent_business_access order by company_id')).rows, access);

  await db.exec("select set_config('request.jwt.claim.sub','',false);set role anon");
  await assert.rejects(reclassify(atomic), /permission denied/);
  await assert.rejects(db.query('select * from public.urgent_exercise_reclassifications'), /permission denied/);
  assert.deepEqual((await db.query('select public.urgent_exercise_reclassification_policy() policy')).rows[0].policy, {
   enabled: true, version: '20261031-exercise-reclassification', admin_only: true,
  });
  console.log('PASS exercise reclassification: admin/confirmation, pre-loading states, invoice guards, exact residual credit, atomic rollback, immutable issued documents, test marker on new versions, replay and unchanged subscriptions/access.');
 } finally { await db.close(); }
})().catch(error => { console.error(error); process.exit(1); });

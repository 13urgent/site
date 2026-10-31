const { createDatabase } = require('./helpers/pilot-database.cjs');
const fs = require('fs');
const assert = require('assert/strict');

(async () => {
 const { db, actor, uid } = await createDatabase({ includeBilling: false });
 try {
  for (const name of [
   '202610200001_manual_commerce.sql',
   '202610220001_carrier_shipper.sql',
   '202610270002_document_renewal.sql',
   '202610310002_internal_premium.sql',
   '202610310003_start_reauthorization.sql',
  ]) await db.exec(fs.readFileSync(__dirname + '/../supabase/migrations/' + name, 'utf8'));

  const terms = 'PRO-B2B-2026-10-20-v3';
  await actor(1);
  await db.query("select public.urgent_set_commercial_mode(true,'CHRONOSS - VIREMENTS ET FACTURATION MANUELLE')");
  for (const n of [2, 3]) {
   await actor(n);
   await db.query('select public.urgent_accept_terms($1)', [terms]);
  }

  async function ready(expected, message) {
   await actor(3);
   assert.equal((await db.query('select public.urgent_carrier_ready($1) ready', [uid(3)])).rows[0].ready, expected, message);
  }
  async function approveStart() {
   await actor(1);
   await db.query("select public.urgent_review_pilot($1,'91871039300052','basics',true,true)", [uid(3)]);
  }
  async function payment(state) {
   await db.exec('reset role');
   await db.query('delete from public.urgent_manual_subscriptions where company_id=$1', [uid(3)]);
   const [start, end, revoked] = {
    expired: ["now()-interval '2 months'", "now()-interval '1 month'", 'null'],
    revoked: ["now()-interval '1 day'", "now()+interval '1 month'", 'now()'],
    future: ["now()+interval '1 day'", "now()+interval '1 month'", 'null'],
    active: ["now()-interval '1 day'", "now()+interval '1 month'", 'null'],
   }[state];
   // Database-owner setup models lifecycle events; no real company or bank data.
   await db.query(`insert into public.urgent_manual_subscriptions(
    company_id,plan,starts_at,ends_at,expected_ttc_cents,received_cents,
    bank_reference,invoice_reference,recorded_by,revoked_at
   )values($1,'bronze',${start},${end},1500,1500,'TEST-START-BANK','TEST-START-INVOICE',$2,${revoked})`, [uid(3), uid(1)]);
  }
  async function course() {
   await actor(2);
   const sid = (await db.query("select public.urgent_publish_shipment('Marseille','Lyon',now()+interval '7 days','Porteur',1,300,'Client','client@example.com','') id")).rows[0].id;
   await actor(3);
   const offer = (await db.query('select public.urgent_submit_offer($1,450) id', [sid])).rows[0].id;
   await actor(2);
   return offer;
  }
  const accept = offer => db.query('select public.urgent_accept_commercial_offer($1,450,675,$2,true)', [offer, terms]);

  await approveStart();
  await ready(true, 'An approved Start with no paid history remains available');

  for (const state of ['expired', 'revoked', 'future']) {
   await payment(state);
   await ready(false, 'A stale Start decision cannot bypass a newly recorded ' + state + ' period');
   await approveStart();
   await ready(true, 'Explicit new Start approval can follow a ' + state + ' period');
  }

  // Equal timestamps do not prove that Start was approved after the paid event.
  await db.exec('reset role');
  await db.query('update public.urgent_business_access set reviewed_at=(select recorded_at from public.urgent_manual_subscriptions where company_id=$1) where company_id=$1', [uid(3)]);
  await ready(false, 'Ambiguous equal timestamps require a fresh administrator decision');
  await approveStart();

  // A Start bridge before a future period must not survive that period's end.
  await db.exec('reset role');
  await db.query("update public.urgent_business_access set reviewed_at=now()-interval '3 days' where company_id=$1", [uid(3)]);
  await db.query("update public.urgent_manual_subscriptions set recorded_at=now()-interval '4 days',starts_at=now()-interval '2 days',ends_at=now()-interval '1 day' where company_id=$1", [uid(3)]);
  await ready(false, 'A decision before a paid period ended cannot automatically restore Start');
  await approveStart();
  await ready(true, 'Start can be explicitly restored after paid expiry');

  // Revocation is a later event; a revoked future end is not a second event.
  await db.exec('reset role');
  await db.query('update public.urgent_manual_subscriptions set revoked_at=now() where company_id=$1', [uid(3)]);
  await ready(false, 'Revocation invalidates an older Start approval');
  await approveStart();
  await ready(true, 'A new Start decision after revocation is sufficient');
  await payment('revoked');
  await approveStart();
  await ready(true, 'A revoked period can be followed by Start before its original scheduled end');
  await db.exec('reset role');
  await db.query("update public.urgent_manual_subscriptions set ends_at=now()-interval '1 hour' where company_id=$1", [uid(3)]);
  await ready(true, 'A revoked period reaching its original end does not revoke a newer Start decision');

  // Every paid row matters, including one outside the latest starts_at period.
  await db.exec('reset role');
  await db.query(`insert into public.urgent_manual_subscriptions(
   company_id,plan,starts_at,ends_at,expected_ttc_cents,received_cents,
   bank_reference,invoice_reference,recorded_by,recorded_at,revoked_at
  )values($1,'silver',now()-interval '3 months',now()-interval '2 months',4000,4000,
   'TEST-OLDER-BANK','TEST-OLDER-INVOICE',$2,now()-interval '3 months',now())`, [uid(3), uid(1)]);
  await ready(false, 'A later revocation of an older paid row also requires a new decision');
  await approveStart();
  await ready(true, 'A decision after all paid events can restore Start');

  // No request metadata or non-administrator RPC can authorize Start.
  await actor(3);
  await assert.rejects(db.query("select public.urgent_review_pilot($1,'91871039300052','basics',true,true)", [uid(3)]), /Administration/);
  await db.exec('reset role');
  await db.query("update public.urgent_business_access set plan='gold' where company_id=$1", [uid(3)]);
  await db.query('update auth.users set raw_user_meta_data=$1 where id=$2', [JSON.stringify({ subscription_plan_request: 'basics' }), uid(3)]);
  await ready(false, 'A declarative Start request cannot activate Start');
  await approveStart();

  // Existing documents, current terms and establishment authorization still apply.
  await db.exec('reset role');
  await db.query("update public.carrier_documents set review_status='pending' where company_id=$1 and document_type='insurance_goods'", [uid(3)]);
  await ready(false, 'Start does not bypass document approval');
  await db.exec('reset role');
  await db.query("update public.carrier_documents set review_status='approved' where company_id=$1", [uid(3)]);
  await db.query('delete from public.urgent_terms_acceptances where company_id=$1', [uid(3)]);
  await ready(false, 'Start does not bypass current terms');
  await actor(3);
  await db.query('select public.urgent_accept_terms($1)', [terms]);
  await db.exec('reset role');
  await db.query('update public.urgent_business_access set pilot_enabled=false where company_id=$1', [uid(3)]);
  await ready(false, 'Start does not bypass establishment authorization');
  await approveStart();

  // Reauthorized Start retains its one-course Paris calendar-month limit.
  await accept(await course());
  await assert.rejects(accept(await course()), /Quota/);

  // Active paid Drive takes precedence over Start and uses its actual quota.
  await payment('active');
  await ready(true, 'Active paid access needs no separate Start approval');
  await actor(1);
  await db.query("select public.urgent_review_pilot($1,'91871039300052','gold',true,true)", [uid(3)]);
  // Exclude the preceding Start course from the new paid period's usage.
  await db.exec('reset role');
  await db.query('update public.urgent_manual_subscriptions set recorded_at=now() where company_id=$1', [uid(3)]);
  for (let i = 0; i < 5; i++) await accept(await course());
  await assert.rejects(accept(await course()), /Quota/);

  // Internal Premium remains a separate entitlement and creates no bank period.
  await payment('expired');
  await ready(false, 'Expired paid access alone remains blocked');
  await actor(1);
  const today = (await db.query("select (now()at time zone'Europe/Paris')::date::text d")).rows[0].d;
  const before = (await db.query('select count(*)::int n from public.urgent_manual_subscriptions')).rows[0].n;
  await db.query('select public.urgent_grant_internal_premium($1,$2,$3,$3,$4,true)', [uid(80), uid(3), today, 'Période interne fictive pour vérifier les droits']);
  await ready(true, 'Internal Premium remains available independently of Start history');
  await actor(1);
  assert.equal((await db.query('select count(*)::int n from public.urgent_manual_subscriptions')).rows[0].n, before);
  for (let i = 0; i < 2; i++) await accept(await course());
  await actor(1);
  await db.query('select public.urgent_revoke_internal_premium($1,$2)', [uid(80), 'Retrait de la période de test interne']);
  await ready(false, 'Ending internal Premium does not bypass a blocked paid-history decision');

  // A client remains a donneur d'ordre; approval cannot change a server role.
  await actor(2);
  await assert.rejects(db.query('select public.urgent_submit_offer($1,450)', [uid(999)]), /transporteur/);
  await db.exec('reset role;set role anon');
  await assert.rejects(db.query('select public.urgent_carrier_ready($1)', [uid(3)]), /permission denied/);
  assert.deepEqual((await db.query('select public.urgent_start_access_policy() policy')).rows[0].policy, {
   enabled: true,
   version: '20261031-start-reauthorization',
   monthly_quota: 1,
   admin_decision_required: true,
  });
  await actor(3);
  assert.equal((await db.query('select public.urgent_start_access_policy() policy')).rows[0].policy.version, '20261031-start-reauthorization');
  console.log('PASS Start reauthorization: explicit admin decision after paid lifecycle, no automatic fallback, Start/paid/internal quotas, documents/terms/authorization and roles preserved.');
 } finally {
  await db.close();
 }
})().catch(error => { console.error(error); process.exit(1); });

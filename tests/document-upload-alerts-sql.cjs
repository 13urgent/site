const{createDatabase}=require('./helpers/pilot-database.cjs');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const{db,uid,actor}=await createDatabase({includeBilling:false});
 try{
  await db.exec(`alter table public.carrier_documents add column original_filename text;alter table public.carrier_documents add column storage_path text;grant select,insert on public.carrier_documents to authenticated;alter table public.carrier_documents enable row level security;create policy original_document_insert on public.carrier_documents for insert to authenticated with check(public.urgent_actor_role()='carrier'and company_id=public.urgent_actor_company()and review_status='pending');create policy original_document_read on public.carrier_documents for select to authenticated using(company_id=public.urgent_actor_company());create schema storage;create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text);grant usage on schema storage to authenticated;grant select,insert on storage.objects to authenticated;alter table storage.objects enable row level security;create policy carrier_file_insert on storage.objects for insert to authenticated with check(public.urgent_actor_role()='carrier'and bucket_id='carrier-documents'and split_part(name,'/',1)=public.urgent_actor_company()::text);create policy carrier_file_read on storage.objects for select to authenticated using(public.urgent_actor_role()='carrier'and bucket_id='carrier-documents'and split_part(name,'/',1)=public.urgent_actor_company()::text);`);
  // Les politiques et le contrôle du fichier restent testés séparément : ici la file
  // réagit à une insertion autorisée, y compris depuis un autre client que le site.
  await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610290001_document_upload_alerts.sql','utf8'));
  assert.equal(Number((await db.query('select count(*)as n from public.urgent_document_alerts')).rows[0].n),0);
  let serial=0;
  const deposit=async(n)=>{await actor(n);const name=uid(n)+'/'+(++serial)+'.pdf';await db.query("insert into storage.objects(bucket_id,name)values('carrier-documents',$1)",[name]);return(await db.query("insert into public.carrier_documents(company_id,document_type,review_status,original_filename,storage_path)values($1,'registration','pending','kbis.pdf',$2)returning id",[uid(n),name])).rows[0].id;};
  const docs=[await deposit(3),await deposit(3),await deposit(2)];
  assert.equal((await db.query('select id from public.carrier_documents where id=$1',[docs[0]])).rows.length,0);
  const forge=(company,path,kind='registration',status='pending')=>db.query('insert into public.carrier_documents(company_id,document_type,review_status,storage_path)values($1,$2,$3,$4)',[company,kind,status,path]);
  await assert.rejects(forge(uid(3),uid(3)+'/1.pdf'),/row-level security/);
  await assert.rejects(forge(uid(2),uid(3)+'/1.pdf'),/row-level security/);
  await assert.rejects(forge(uid(2),uid(2)+'/absent.pdf'),/row-level security/);
  await assert.rejects(forge(uid(2),uid(2)+'/3.pdf','transport_licence'),/row-level security/);
  await assert.rejects(forge(uid(2),uid(2)+'/3.pdf','registration','approved'),/row-level security/);
  await assert.rejects(db.query("insert into storage.objects(bucket_id,name)values('carrier-documents',$1)",[uid(3)+'/forged.pdf']),/row-level security/);
  await assert.rejects(db.query("insert into storage.objects(bucket_id,name)values('carrier-documents',$1)",[uid(2)+'/../forged.pdf']),/row-level security/);
  await assert.rejects(db.query('select * from public.urgent_document_alerts'),/permission denied/);
  await assert.rejects(db.query('select * from public.urgent_claim_document_alerts()'),/permission denied/);
  await assert.rejects(db.query('select public.urgent_finish_document_alert($1,$1,true)',[uid(90)]),/permission denied/);
  await db.exec('reset role');
  await db.query("update public.carrier_documents set review_status='approved'where id=$1",[docs[0]]);
  assert.equal(Number((await db.query('select count(*)as n from public.urgent_document_alerts')).rows[0].n),3);
  await db.exec('set role service_role');
  let jobs=(await db.query('select * from public.urgent_claim_document_alerts()')).rows;
  assert.equal(jobs.length,3);assert.equal(jobs.filter(r=>r.account_type==='client').length,1);assert.equal(jobs.filter(r=>r.account_type==='carrier').length,2);
  assert(jobs.every(r=>docs.includes(r.document_id)&&r.original_filename==='kbis.pdf'));
  assert.equal((await db.query('select * from public.urgent_claim_document_alerts()')).rows.length,0);
  const job=jobs[0],failed=jobs[1];
  assert.equal((await db.query('select public.urgent_finish_document_alert($1,$2,true,$3,null)ok',[job.alert_id,uid(99),'wrong'])).rows[0].ok,false);
  assert.equal((await db.query('select public.urgent_finish_document_alert($1,$2,true,$3,null)ok',[job.alert_id,job.lease_token,'provider-id'])).rows[0].ok,true);
  await db.query('select public.urgent_finish_document_alert($1,$2,false,null,$3)',[failed.alert_id,failed.lease_token,'provider_http_429']);
  await db.exec('reset role');
  assert.equal((await db.query('select status from public.urgent_document_alerts where id=$1',[job.alert_id])).rows[0].status,'sent');
  const retry=(await db.query('select * from public.urgent_document_alerts where id=$1',[failed.alert_id])).rows[0];assert.equal(retry.status,'pending');assert(retry.next_attempt_at>retry.created_at);
  await db.query("update public.urgent_document_alerts set next_attempt_at=now()-interval '1 minute'where id=$1",[failed.alert_id]);
  jobs=(await db.query('select * from public.urgent_claim_document_alerts()')).rows;assert.equal(jobs.length,1);assert.notEqual(jobs[0].lease_token,failed.lease_token);
  await db.query("update public.urgent_document_alerts set locked_until=now()-interval '1 minute'where id=$1",[failed.alert_id]);assert.equal((await db.query('select * from public.urgent_claim_document_alerts()')).rows.length,1);
  await db.query('update public.urgent_document_alerts set attempts=8,locked_until=null where id=$1',[failed.alert_id]);await db.query('select * from public.urgent_claim_document_alerts()');assert.equal((await db.query('select status from public.urgent_document_alerts where id=$1',[failed.alert_id])).rows[0].status,'failed');
  await deposit(4);await db.exec('reset role');await db.query("update public.urgent_document_alerts set created_at=now()-interval '24 hours'where user_id=$1",[uid(4)]);await db.query('select * from public.urgent_claim_document_alerts()');assert.equal((await db.query('select last_error_code from public.urgent_document_alerts where user_id=$1',[uid(4)])).rows[0].last_error_code,'delivery_window_expired');
  const count=Number((await db.query('select count(*)as n from public.urgent_document_alerts')).rows[0].n);
  await actor(1);await db.exec('reset role');await db.query("insert into public.carrier_documents(company_id,document_type,review_status)values($1,'registration','pending')",[uid(1)]);assert.equal(Number((await db.query('select count(*)as n from public.urgent_document_alerts')).rows[0].n),count);
  await db.exec("select set_config('request.jwt.claim.sub','',false);set role anon");assert.equal((await db.query('select public.urgent_document_alert_policy()p')).rows[0].p.enabled,true);await assert.rejects(db.query('select * from public.urgent_claim_document_alerts()'),/permission denied/);
  console.log('PASS file documents : pas de reprise historique, plusieurs pièces, transporteur/donneur d’ordre, aucune alerte sur approbation, accès serveur seul, baux exclusifs, accusés protégés, retry, reprise après panne et expiration 23 h.');
 }finally{await db.close();}
})().catch(e=>{console.error(e);process.exit(1)});

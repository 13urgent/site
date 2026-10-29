const{createDatabase}=require('./helpers/pilot-database.cjs');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const{db,uid,actor}=await createDatabase({includeBilling:false});
 try{
  await db.exec(`alter table auth.users add column email_confirmed_at timestamptz;update auth.users set email_confirmed_at=now();create schema storage;create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,owner_id text,metadata jsonb);grant usage on schema storage to anon,authenticated;grant select,insert,update,delete on storage.objects to anon,authenticated;alter table storage.objects enable row level security;create policy legacy_open_storage on storage.objects for all to authenticated,anon using(true)with check(true);`);
  for(const name of['202610280002_archive_shipments.sql','202610290002_mobile_missions.sql'])await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/'+name,'utf8'));
  await actor(2);const sid=(await db.query("select public.urgent_publish_shipment('Marseille','Lyon',now()+interval '7 days','Porteur',1,100,'Client','private@example.com','Instructions privées')id")).rows[0].id;
  const addresses=()=>db.query('select public.urgent_save_mission_addresses($1,$2,$3)',[sid,'10 rue du Départ, 13015 Marseille','20 rue de la Livraison, 69001 Lyon']);
  await addresses();await actor(4);await assert.rejects(addresses(),/propriétaire/);assert.equal((await db.query('select * from public.urgent_shipment_private where shipment_id=$1',[sid])).rows.length,0);
  await actor(3);const offer=(await db.query('select public.urgent_submit_offer($1,450)id',[sid])).rows[0].id;await actor(2);await db.query('select public.urgent_accept_offer($1,true,450)',[offer]);await addresses();
  const store=async(id,mime='image/jpeg',size=1024,owner=3)=>{const path=sid+'/'+uid(id)+(mime==='application/pdf'?'.pdf':'.jpg');await db.query("insert into storage.objects(bucket_id,name,owner_id,metadata)values('urgent-mission-files',$1,$2,$3)",[path,uid(owner),{mimetype:mime,size}]);return path;};
  const add=(id,kind,path,caption='')=>db.query('select public.urgent_add_mission_file($1,$2,$3,$4,$5,$6)id',[sid,uid(id),kind,caption,kind==='waybill'?'lettre.pdf':'photo.jpg',path]);
  await actor(4);await assert.rejects(store(90),/row-level security/);await assert.rejects(add(90,'goods',sid+'/'+uid(90)+'.jpg'),/attribué/);
  await actor(3);const photo=await store(90);assert.equal((await db.query('select * from storage.objects where name=$1',[photo])).rows.length,0);
  await assert.rejects(add(90,'reservation',photo,'court'),/réserves/);
  await add(90,'goods',photo);await add(90,'goods',photo);await assert.rejects(add(90,'waybill',photo),/déjà utilisée/);
  assert.equal((await db.query('select * from storage.objects where name=$1',[photo])).rows.length,1);
  const cmr=await store(91,'application/pdf');await add(91,'waybill',cmr);
  const reservation=await store(92);await add(92,'reservation',reservation,'Palette abîmée sur le côté droit, constatée au chargement.');
  const badOwner=await store(93,'image/jpeg',1024,4);await assert.rejects(add(93,'goods',badOwner),/ce compte/);
  const tooBig=await store(94,'image/jpeg',10485761);await assert.rejects(add(94,'goods',tooBig),/taille/);
  const wrongMime=await store(95,'image/svg+xml');await assert.rejects(add(95,'goods',wrongMime),/Format/);
  await assert.rejects(db.query('insert into public.urgent_mission_files(id)values($1)',[uid(99)]),/permission denied/);
  assert.equal((await db.query('delete from storage.objects where name=$1 returning id',[photo])).rows.length,0);
  assert.equal((await db.query("update storage.objects set name='changed'where name=$1 returning id",[photo])).rows.length,0);
  for(const next of['heading_pickup','at_pickup','loaded','delivery_reported'])await db.query('select public.urgent_progress_shipment($1,$2)',[sid,next]);
  await actor(2);await assert.rejects(addresses(),/figées/);assert.equal((await db.query('select * from public.urgent_mission_files where shipment_id=$1',[sid])).rows.length,3);assert.equal((await db.query('select * from storage.objects where name=$1',[cmr])).rows.length,1);
  await assert.rejects(db.query("select public.urgent_progress_shipment($1,'completed')",[sid]),/signalement/);
  await actor(4);assert.equal((await db.query('select * from public.urgent_mission_files where shipment_id=$1',[sid])).rows.length,0);assert.equal((await db.query('select * from storage.objects where name=$1',[photo])).rows.length,0);await assert.rejects(db.query('select * from public.urgent_claim_mission_notifications()'),/permission denied/);
  await actor(1);const incident=(await db.query('select id from public.urgent_shipment_incidents where shipment_id=$1',[sid])).rows[0].id;await db.query('select public.urgent_resolve_incident($1,$2)',[incident,'Réserves examinées avec les deux parties et traitées.']);await actor(2);await db.query("select public.urgent_progress_shipment($1,'completed')",[sid]);
  await db.exec('reset role');assert.equal(Number((await db.query('select count(*)n from public.urgent_mission_notifications')).rows[0].n),5);assert.equal(Number((await db.query('select count(*)n from public.urgent_mission_files')).rows[0].n),3);
  await db.exec('set role service_role');let jobs=(await db.query('select * from public.urgent_claim_mission_notifications()')).rows;assert.equal(jobs.length,3);assert(jobs.every(j=>j.recipient_email==='test2@example.com'&&j.recipient_confirmed&&j.recipient_allowed));
  assert.equal((await db.query('select public.urgent_finish_mission_notification($1,$2,true,$3,null)ok',[jobs[0].alert_id,uid(999),'bad'])).rows[0].ok,false);
  for(const j of jobs)assert.equal((await db.query('select public.urgent_finish_mission_notification($1,$2,true,$3,null)ok',[j.alert_id,j.lease_token,'provider-id'])).rows[0].ok,true);
  jobs=(await db.query('select * from public.urgent_claim_mission_notifications()')).rows;assert.equal(jobs.length,2);await db.query("select public.urgent_finish_mission_notification($1,$2,false,null,'provider_http_429')",[jobs[0].alert_id,jobs[0].lease_token]);
  await db.exec('reset role');await db.query('update public.urgent_mission_notifications set attempts=8,locked_until=null where id=$1',[jobs[0].alert_id]);await db.query('select * from public.urgent_claim_mission_notifications()');assert.equal((await db.query('select status from public.urgent_mission_notifications where id=$1',[jobs[0].alert_id])).rows[0].status,'failed');
  await actor(3);const late=await store(96);await add(96,'waybill',late); // Réception tardive de la copie après confirmation.
  await db.exec('reset role');await db.query('update public.urgent_shipments set is_test=true where id=$1',[sid]);await actor(3);const fake=await store(97);await add(97,'goods',fake);await db.exec('reset role');assert.equal(Number((await db.query('select count(*)n from public.urgent_mission_notifications')).rows[0].n),6);
  await db.query("update public.urgent_shipments set status='cancelled'where id=$1",[sid]);await actor(3);await assert.rejects(store(98),/row-level security/);
  await db.exec("reset role;select set_config('request.jwt.claim.sub','',false);set role anon");assert.equal((await db.query('select * from storage.objects where name=$1',[photo])).rows.length,0);await assert.rejects(db.query('select * from public.urgent_mission_files'),/permission denied/);await assert.rejects(db.query('select public.urgent_add_mission_file($1,$2,$3,$4,$5,$6)',[sid,uid(99),'goods','','x.jpg','x']),/permission denied/);
  console.log('PASS missions mobiles SQL : adresses privées, transporteur attribué seul, stockage fermé même avec ancienne politique large, contrôles du fichier reçu et de son propriétaire, idempotence, réserves bloquant la confirmation, pièces tardives, notifications au vrai donneur d’ordre, exercices exclus et baux protégés.');
 }finally{await db.close();}
})().catch(e=>{console.error(e);process.exit(1)});

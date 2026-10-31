// SQL local uniquement : sept comptes fictifs, aucune suppression de production.
const {createDatabase}=require('./helpers/pilot-database.cjs');
const fs=require('fs'),assert=require('assert/strict');
(async()=>{
 const {db,actor,uid}=await createDatabase({includeBilling:false});
 try{
  await db.exec(`alter table auth.users add column email_confirmed_at timestamptz default now(),add column deleted_at timestamptz,add column banned_until timestamptz,add column encrypted_password text default 'FAKE-HASH',add column phone text,add column email_change text default '',add column phone_change text default '',add column confirmation_token text default 'FAKE-TOKEN',add column recovery_token text default 'FAKE-TOKEN',add column email_change_token_current text default '',add column email_change_token_new text default '',add column phone_change_token text default '',add column raw_app_meta_data jsonb default '{}',add column updated_at timestamptz default now();
   create table auth.identities(id uuid primary key default gen_random_uuid(),user_id uuid references auth.users(id));
   create table auth.sessions(id uuid primary key default gen_random_uuid(),user_id uuid references auth.users(id));
   create table auth.refresh_tokens(id uuid primary key default gen_random_uuid(),user_id text);
   create schema storage;create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,owner_id text,metadata jsonb);alter table storage.objects enable row level security;grant usage on schema storage to authenticated;grant select on storage.objects to authenticated;create policy legacy_object_access on storage.objects for select to authenticated using(true);
   alter table public.profiles enable row level security;alter table public.companies enable row level security;grant select on public.profiles,public.companies to authenticated;create policy fixture_profiles on public.profiles for select to authenticated using(true);create policy fixture_companies on public.companies for select to authenticated using(true);`);
  for(const n of[5,6,7]){
   await db.query('insert into auth.users(id,email)values($1,$2)',[uid(n),'test'+n+'@example.com']);
   await db.query('insert into public.companies values($1,$2)',[uid(n),'Entreprise fictive '+n]);
   await db.query("insert into public.profiles values($1,$1,'carrier')",[uid(n)]);
   await db.query("insert into public.urgent_business_access(company_id,siret,registry_checked,pilot_enabled,plan,reviewed_by)values($1,'91871039300052',true,true,'gold',$2)",[uid(n),uid(1)]);
  }
  for(const name of['202610200001_manual_commerce.sql','202610220001_carrier_shipper.sql','202610270002_document_renewal.sql','202610280001_edit_shipments.sql','202610280002_archive_shipments.sql','202610290002_mobile_missions.sql','202610300001_shipment_schedule.sql','202610300002_platform_services.sql','202610310001_transport_dossier.sql','202610310002_internal_premium.sql','202610310003_start_reauthorization.sql'])await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/'+name,'utf8'));
  await db.exec(fs.readFileSync(__dirname+'/../supabase/setup/open-transport-documents.sql','utf8'));
  await db.exec('insert into auth.identities(user_id)select id from auth.users;insert into auth.sessions(user_id)select id from auth.users;insert into auth.refresh_tokens(user_id)select id::text from auth.users;');
  await actor(2);const shipment=(await db.query("select public.urgent_publish_shipment('Ville A','Ville B',now()+interval'7 days','Porteur',1,500,'Client fictif','client@example.com','Marchandise fictive')id")).rows[0].id;
  await actor(3);const offer=(await db.query('select public.urgent_submit_offer($1,450)id',[shipment])).rows[0].id;
  await actor(2);await db.query('select public.urgent_accept_offer($1,true,450)',[offer]);
  const data={consignor_name:'Client fictif',consignor_address:'Adresse de départ fictive',consignee_name:'Destinataire fictif',consignee_address:'Adresse de livraison fictive',goods_description:'Marchandise fictive'};
  await db.query('select public.urgent_save_document_branding(0,$1)',[{address:'Adresse fictive de l’entreprise donneur d’ordre'}]);
  await db.query("select public.urgent_save_transport_document($1,$2,'confirmation',0,'issued',$3,true)",[uid(90),shipment,data]);
  await db.exec('reset role');await db.query("insert into storage.objects(bucket_id,name,owner_id)values('urgent-mission-files','historique-fictif.pdf',$1)",[uid(2)]);
  const keptIds=[uid(1),uid(3),uid(4)];const keptBefore=(await db.query('select to_jsonb(u)r from auth.users u where id=any($1::uuid[])order by id',[keptIds])).rows;
  const publicBefore={};for(const table of['urgent_shipments','urgent_offers','urgent_transport_documents','urgent_shipment_events'])publicBefore[table]=(await db.query('select * from public.'+table+' order by id')).rows;
  const migration=fs.readFileSync(__dirname+'/../supabase/migrations/202610310008_account_cleanup.sql','utf8');await db.exec(migration);await db.exec(migration);
  const keep=['test1@example.com','test3@example.com','test4@example.com'];const remove=['test2@example.com','test5@example.com','test6@example.com','test7@example.com'];
  const close=(request=uid(901),k=keep,r=remove)=>db.query('select public.urgent_close_login_accounts($1,$2,$3,$4,$5)r',[request,k,r,keep[0],'Clôture des quatre comptes fictifs sur demande']);
  await assert.rejects(close(uid(902),[keep[0],keep[1],'absent@example.com']),/conserver/);
  assert.equal((await db.query('select count(*)::int n from public.urgent_closed_accounts')).rows[0].n,0);
  await db.query('insert into auth.users(id,email)values($1,$2)',[uid(8),'unexpected@example.com']);
  await assert.rejects(close(),/non prévu/);assert.equal((await db.query('select count(*)::int n from auth.users where deleted_at is not null')).rows[0].n,0);
  await db.query('delete from auth.users where id=$1',[uid(8)]);
  await actor(1);await assert.rejects(close(),/permission denied/);await db.exec('reset role');
  let result;if(process.argv[2]){let packet=fs.readFileSync(process.argv[2],'utf8');const mapping=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));for(const[from,to]of Object.entries(mapping))packet=packet.replaceAll(from,to);await db.exec(packet);result=(await db.query('select result from public.urgent_account_cleanup_runs where id=$1',[uid(901)])).rows[0].result;}else result=(await close()).rows[0].r;assert.equal(result.active_accounts,3);assert.equal(result.removed_accounts.length,4);assert.equal(result.history_preserved,true);
  assert.deepEqual((await db.query('select to_jsonb(u)r from auth.users u where id=any($1::uuid[])order by id',[keptIds])).rows,keptBefore,'Preserved authentication records must remain byte-for-byte equal');
  for(const table of Object.keys(publicBefore))assert.deepEqual((await db.query('select * from public.'+table+' order by id')).rows,publicBefore[table],table+' history must stay unchanged');
  for(const table of['identities','sessions','refresh_tokens'])assert.equal((await db.query('select count(*)::int n from auth.'+table)).rows[0].n,3);
  assert.equal((await db.query('select count(*)::int n from public.urgent_closed_accounts')).rows[0].n,4);
  assert.equal((await close()).rows[0].r.reused,true);await assert.rejects(close(uid(901),keep,[...remove].reverse()),/autre demande/);
  for(const n of[2,5,6,7]){
   await actor(n);assert.equal((await db.query('select public.urgent_actor_role()r')).rows[0].r,null);assert.equal((await db.query('select public.urgent_actor_company()r')).rows[0].r,null);
   assert.equal((await db.query('select * from public.profiles')).rows.length,0);assert.equal((await db.query('select * from public.urgent_shipments')).rows.length,0);assert.equal((await db.query('select * from storage.objects')).rows.length,0);
   await assert.rejects(db.query('select public.urgent_transport_document($1)',[uid(90)]),/parties/);
  }
  await actor(1);assert.equal((await db.query('select * from public.companies')).rows.length,3);assert.equal((await db.query('select * from public.profiles')).rows.length,3);
  assert.equal((await db.query("select * from public.urgent_transport_document_directory('',0)")).rows.length,3);
  assert.equal((await db.query('select * from public.urgent_pilot_directory()')).rows.length,2);
  assert.equal((await db.query('select public.urgent_transport_document($1)d',[uid(90)])).rows[0].d.id,uid(90));
  await actor(3);assert.equal((await db.query('select * from public.urgent_shipments')).rows.length,1);assert.equal((await db.query('select public.urgent_transport_document($1)d',[uid(90)])).rows[0].d.id,uid(90),'Surviving carrier keeps access to historical documents');
  console.log('PASS clôture comptes : 3 conservés inchangés, 4 connexions supprimées, moyens de connexion révoqués, JWT anciens refusés, annuaires nettoyés, documents/historiques intacts, reprises et refus d’un compte imprévu.');
 }finally{await db.close()}
})().catch(e=>{console.error(e);process.exit(1)});

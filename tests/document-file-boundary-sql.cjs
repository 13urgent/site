const{createDatabase}=require('./helpers/pilot-database.cjs');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const{db,uid,actor}=await createDatabase({includeBilling:false});
 await db.exec(`create schema storage;create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text);grant usage on schema storage to authenticated;grant select on storage.objects to authenticated;alter table storage.objects enable row level security;create policy storage_read_own on storage.objects for select to authenticated using(bucket_id='carrier-documents' and split_part(name,'/',1)=public.urgent_actor_company()::text);alter table public.carrier_documents add column storage_path text;grant select,insert on public.carrier_documents to authenticated;alter table public.carrier_documents enable row level security;create policy old_document_insert on public.carrier_documents for insert to authenticated with check(company_id=public.urgent_actor_company() and review_status='pending' and reviewed_by is null and reviewed_at is null);create policy document_read_own on public.carrier_documents for select to authenticated using(company_id=public.urgent_actor_company());grant update(role) on public.profiles to authenticated;create policy "Update own basic profile" on public.profiles for update to authenticated using(id=auth.uid()) with check(id=auth.uid());`);
 for(const n of [3,4])for(const filename of ['valid.pdf','..','../bad.pdf','x\\bad.pdf'])await db.query("insert into storage.objects(bucket_id,name) values('carrier-documents',$1)",[uid(n)+'/'+filename]);
 await db.exec('create policy legacy_document_insert_open on public.carrier_documents for insert to authenticated with check(true);');
 const before=(await db.query('select count(*)::int n from public.carrier_documents')).rows[0].n;
 const sql=fs.readFileSync(__dirname+'/../supabase/migrations/202610230002_document_file_boundary.sql','utf8');await db.exec(sql);await db.exec(sql);
 await actor(3);
 const insert=(company,path,status='pending')=>db.query("insert into public.carrier_documents(company_id,document_type,review_status,storage_path)values($1,'insurance_rc',$3,$2)",[company,path,status]);
 await insert(uid(3),uid(3)+'/valid.pdf');
 for(const path of [uid(4)+'/valid.pdf',uid(3)+'/absent.pdf',uid(3)+'/../bad.pdf',uid(3)+'/..',uid(3)+'/x\\bad.pdf',null,'valid.pdf'])await assert.rejects(insert(uid(3),path),/row-level security/);
 await assert.rejects(insert(uid(4),uid(4)+'/valid.pdf'),/row-level security/);
 await assert.rejects(insert(uid(3),uid(3)+'/valid.pdf','approved'),/row-level security/);
 await actor(2);await assert.rejects(insert(uid(2),uid(3)+'/valid.pdf'),/row-level security/);
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.carrier_documents')).rows[0].n,before+1);
 assert.equal((await db.query("select count(*)::int n from pg_policies where tablename='profiles' and policyname='Update own basic profile'")).rows[0].n,0);
 await db.close();console.log('PASS : fichier existant de la bonne entreprise accepté ; autre entreprise, fichier absent, chemins invalides, auto-approbation et client refusés ; pièces historiques conservées');
})().catch(e=>{console.error(e);process.exit(1)});

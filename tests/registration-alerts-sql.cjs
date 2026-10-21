const{PGlite}=require('@electric-sql/pglite');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const db=new PGlite();
 await db.exec(`create role anon;create role authenticated;create role service_role bypassrls;create schema auth;create table auth.users(id uuid primary key,email text,raw_user_meta_data jsonb,email_confirmed_at timestamptz);create table public.companies(id uuid primary key,name text);create table public.profiles(id uuid primary key references auth.users(id),company_id uuid references public.companies(id),role text);`);
 const uid=n=>'00000000-0000-0000-0000-'+String(n).padStart(12,'0');
 async function account(n,role){await db.query('insert into auth.users values($1,$2,$3,null)',[uid(n),`user${n}@example.com`,{business_siret:'12345678901234'}]);await db.query('insert into public.companies values($1,$2)',[uid(n),'Entreprise '+n]);await db.query('insert into public.profiles values($1,$1,$2)',[uid(n),role]);}
 await account(1,'client');await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610210001_registration_alerts.sql','utf8'));
 assert.equal((await db.query('select count(*)::int n from public.urgent_registration_alerts')).rows[0].n,0);
 await account(2,'carrier');await account(3,'client');await account(4,'admin');
 assert.equal((await db.query('select count(*)::int n from public.urgent_registration_alerts')).rows[0].n,2);
 await db.exec('set role authenticated');await assert.rejects(db.query('select * from public.urgent_registration_alerts'));await assert.rejects(db.query('select * from public.urgent_claim_registration_alerts()'));await db.exec('reset role');
 await db.exec('set role service_role');let rows=(await db.query('select * from public.urgent_claim_registration_alerts()')).rows;assert.equal(rows.length,2);assert.equal(rows[0].email_confirmed,false);assert.equal(rows[0].siret,'12345678901234');assert.equal((await db.query('select * from public.urgent_claim_registration_alerts()')).rows.length,0);
 const job=rows.find(r=>r.user_id===uid(2));
 assert.equal((await db.query('select public.urgent_finish_registration_alert($1,$2,true,$3,null) ok',[job.alert_id,uid(99),'bad'])).rows[0].ok,false);
 assert.equal((await db.query('select public.urgent_finish_registration_alert($1,$2,true,$3,null) ok',[job.alert_id,job.lease_token,'provider-test'])).rows[0].ok,true);
 await db.exec('reset role');assert.equal((await db.query('select status from public.urgent_registration_alerts where user_id=$1',[uid(2)])).rows[0].status,'sent');
 const other=rows.find(r=>r.user_id===uid(3));await db.query('select public.urgent_finish_registration_alert($1,$2,false,null,$3)',[other.alert_id,other.lease_token,'provider_http_429']);
 let q=(await db.query('select * from public.urgent_registration_alerts where user_id=$1',[uid(3)])).rows[0];assert.equal(q.status,'pending');assert.equal(q.attempts,1);assert(q.next_attempt_at>q.created_at);
 await db.query("update public.urgent_registration_alerts set next_attempt_at=now()-interval '1 minute' where user_id=$1",[uid(3)]);
 rows=(await db.query('select * from public.urgent_claim_registration_alerts()')).rows;assert.equal(rows.length,1);assert.notEqual(rows[0].lease_token,other.lease_token);
 await db.query("update public.urgent_registration_alerts set locked_until=now()-interval '1 minute' where user_id=$1",[uid(3)]);
 assert.equal((await db.query('select * from public.urgent_claim_registration_alerts()')).rows.length,1);
 await db.query("update public.urgent_registration_alerts set attempts=8,locked_until=null where user_id=$1",[uid(3)]);assert.equal((await db.query('select * from public.urgent_claim_registration_alerts()')).rows.length,0);
 assert.equal((await db.query('select status from public.urgent_registration_alerts where user_id=$1',[uid(3)])).rows[0].status,'failed');
 await account(5,'client');await db.query("update public.urgent_registration_alerts set created_at=now()-interval '24 hours' where user_id=$1",[uid(5)]);await db.query('select * from public.urgent_claim_registration_alerts()');assert.equal((await db.query('select last_error_code from public.urgent_registration_alerts where user_id=$1',[uid(5)])).rows[0].last_error_code,'delivery_window_expired');
 console.log('PASS alertes SQL : pas de reprise, clients/transporteurs uniquement, permissions, baux, reprise après panne, temporisation, limite et délai 23 h');await db.close();
})().catch(e=>{console.error(e);process.exit(1)});

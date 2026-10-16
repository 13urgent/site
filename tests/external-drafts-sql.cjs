// Exécution : NODE_PATH=/workspace/13urgent-tools/node_modules node tests/external-drafts-sql.cjs
const {PGlite}=require('@electric-sql/pglite');const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{const db=new PGlite();await db.exec(`
create role anon;create role authenticated;
create schema auth;create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
grant usage on schema auth to authenticated,anon;grant execute on function auth.uid() to authenticated,anon;
create table public.profiles(id uuid primary key,role text);
grant select on public.profiles to authenticated;
insert into auth.users values ('00000000-0000-0000-0000-000000000001'),('00000000-0000-0000-0000-000000000002');
insert into public.profiles values ('00000000-0000-0000-0000-000000000001','admin'),('00000000-0000-0000-0000-000000000002','carrier');
`);await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610160001_external_drafts.sql','utf8'));
const actor=async(id)=>db.exec(`reset role;set role authenticated;set request.jwt.claim.sub='00000000-0000-0000-0000-00000000000${id}';`);
await actor(1);await db.exec(`insert into public.urgent_external_drafts(source,origin,destination,budget)values('B2PWeb','Marseille','Lyon',500);`);assert.equal((await db.query('select * from public.urgent_external_drafts')).rows.length,1);
await assert.rejects(db.exec(`insert into public.urgent_external_drafts(source,origin,destination,weight)values('B2PWeb','A','B',-1)`));
await actor(2);assert.equal((await db.query('select * from public.urgent_external_drafts')).rows.length,0);
await assert.rejects(db.exec(`insert into public.urgent_external_drafts(source,origin,destination)values('Rubiwin','A','B')`));
assert.equal((await db.query('delete from public.urgent_external_drafts returning id')).rows.length,0);
await db.exec('reset role;set role anon;');await assert.rejects(db.query('select * from public.urgent_external_drafts'));
await actor(1);assert.equal((await db.query('delete from public.urgent_external_drafts returning id')).rows.length,1);
console.log('PASS migration PostgreSQL, accès admin, refus lecture/écriture transporteur et anonyme, contraintes et suppression');await db.close();})().catch(e=>{console.error(e);process.exit(1)});

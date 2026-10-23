const{createDatabase}=require('./helpers/pilot-database.cjs');const fs=require('fs');const assert=require('assert/strict');
(async()=>{
 const{db,uid,actor}=await createDatabase({includeBilling:false});
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610160001_external_drafts.sql','utf8'));
 // Simule des droits trop larges, y compris un droit par colonne, pour vérifier leur révocation.
 await db.exec('grant all on public.profiles to authenticated;grant update(role),insert(role) on public.profiles to authenticated;alter table public.profiles enable row level security;create policy old_profiles_open on public.profiles for all to authenticated using(true) with check(true);grant select(budget) on public.urgent_external_drafts to authenticated;');
 await actor(1);await db.query("insert into public.urgent_external_drafts(source,origin,destination,budget,notes) values('B2PWeb','TEST A','TEST B',500,'TEST PRIVÉ')");
 await db.exec('reset role');const before=(await db.query('select * from public.urgent_external_drafts')).rows;
 const sql=fs.readFileSync(__dirname+'/../supabase/migrations/202610230001_admin_lockdown.sql','utf8');await db.exec(sql);await db.exec(sql);
 for(const n of [1,2,3]){
  await actor(n);
  try{assert.equal((await db.query('select budget from public.urgent_external_drafts')).rows.length,0);}catch(e){assert(/permission denied/.test(e.message));}
  await assert.rejects(db.query("insert into public.urgent_external_drafts(source,origin,destination)values('B2PWeb','X','Y')"));
  await assert.rejects(db.query('delete from public.urgent_external_drafts'));
  await assert.rejects(db.query("update public.profiles set role='admin' where id=$1",[uid(n)]));
  await assert.rejects(db.query('update public.profiles set company_id=$1 where id=$2',[uid(1),uid(n)]));
  await assert.rejects(db.query('delete from public.profiles where id=$1',[uid(n)]));
  assert.equal((await db.query('select public.urgent_actor_role() role')).rows[0].role,n===1?'admin':n===2?'client':'carrier');
  assert.equal((await db.query('select * from public.profiles')).rows.length,n===1?4:1);
 }
 await db.exec('reset role;set role anon');await assert.rejects(db.query('select * from public.profiles'));await assert.rejects(db.query('select * from public.urgent_external_drafts'));
 await db.exec('reset role');assert.deepEqual((await db.query('select * from public.urgent_external_drafts')).rows,before);
 // La création serveur de profil reste possible sans droit d'insertion pour le navigateur.
 await db.exec("create function public.test_new_profile() returns trigger language plpgsql security definer set search_path='' as $$begin insert into public.profiles(id,company_id,role)values(new.id,null,'client');return new;end;$$;create trigger test_new_profile after insert on auth.users for each row execute function public.test_new_profile();");
 await db.query('insert into auth.users(id,email)values($1,$2)',[uid(9),'server-test@example.com']);assert.equal((await db.query('select role from public.profiles where id=$1',[uid(9)])).rows[0].role,'client');
 await db.close();console.log('PASS verrouillage : budgets/notes suspendus même pour admin, données conservées, droits par colonne révoqués, refus auto-promotion/rattachement, profils limités au propriétaire/admin, création serveur préservée');
})().catch(e=>{console.error(e);process.exit(1)});

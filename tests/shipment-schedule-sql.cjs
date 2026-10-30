const{createDatabase}=require('./helpers/pilot-database.cjs');const fs=require('fs');const assert=require('assert/strict');
(async()=>{const{db,actor,uid}=await createDatabase({includeBilling:false});try{
 await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610280001_edit_shipments.sql','utf8'));
 const start=new Date(Date.now()+7*86400000).toISOString(),end=new Date(Date.now()+8*86400000).toISOString(),later=new Date(Date.now()+9*86400000).toISOString();
 await actor(2);const legacy=(await db.query("select public.urgent_publish_shipment('Paris','Lyon',$1,'Porteur',1,100,'Client','test@example.com','')id",[start])).rows[0].id;
 const migration=fs.readFileSync(__dirname+'/../supabase/migrations/202610300001_shipment_schedule.sql','utf8');await db.exec('reset role');await db.exec(migration);await db.exec(migration);
 assert.equal((await db.query('select delivery_at from public.urgent_shipments where id=$1',[legacy])).rows[0].delivery_at,null);
 const publish=async(arrival=end,test=false)=>db.query("select public.urgent_publish_scheduled_shipment('Paris','Lyon',$1,'Porteur',1,100,'Client','test@example.com','Confidentiel',$2,$3)id",[start,arrival,test]);
 await actor(2);await assert.rejects(publish(start),/postérieure/);await assert.rejects(publish(null),/postérieure/);await assert.rejects(publish(end,true),/administration/);const id=(await publish()).rows[0].id;
 const change=(revision,arrival,ack=false,target=id)=>db.query('select public.urgent_update_scheduled_shipment('+Array.from({length:13},(_,i)=>'$'+(i+1)).join(',')+')r',[target,revision,'Paris','Lyon',start,'Porteur',1,100,'Client','test@example.com','Confidentiel',arrival,ack]);
 await actor(3);const offer=(await db.query('select public.urgent_submit_offer($1,450,0)id',[id])).rows[0].id;await assert.rejects(change(0,later),/propriétaire/);
 await actor(2);await assert.rejects(change(0,start,true),/postérieure/);await assert.rejects(change(0,later),/offres/);assert.deepEqual((await change(0,later,true)).rows[0].r,{revision:1,withdrawn_offers:1,changed:true});assert.deepEqual((await change(1,later)).rows[0].r,{revision:1,withdrawn_offers:0,changed:false});await assert.rejects(change(0,end,true),/changé/);
 await actor(3);assert.equal(new Date((await db.query('select delivery_at from public.urgent_shipments where id=$1',[id])).rows[0].delivery_at).toISOString(),later);await assert.rejects(db.query('select public.urgent_submit_offer($1,450,0)',[id]),/modifiée/);await db.query('select public.urgent_submit_offer($1,475,1)',[id]);
 await actor(2);await db.query('select public.urgent_accept_offer($1,true,475)',[offer]);await assert.rejects(change(1,end,true),/attribution/);
 const old=(await change(0,end,false,legacy)).rows[0].r;assert.equal(old.changed,true);
 await actor(1);const fake=(await publish(end,true)).rows[0].id;assert.equal((await db.query('select is_test from public.urgent_shipments where id=$1',[fake])).rows[0].is_test,true);
 await db.exec('reset role;set role anon');assert.equal((await db.query('select public.urgent_shipment_schedule_policy()p')).rows[0].p.enabled,true);await assert.rejects(publish());
 console.log('PASS horaires SQL : installation rejouable, anciennes arrivées conservées vides, publication atomique, ordre temporel, propriétaire seul, arrivée modifiée = offres retirées/révision, refus après attribution et anonyme, exercices admin seulement.');
}finally{await db.close()}})().catch(e=>{console.error(e);process.exit(1)});

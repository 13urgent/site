const {createDatabase,uid}=require('./helpers/pilot-database.cjs');
const fs=require('fs');
const assert=require('assert/strict');

(async()=>{
 const {db,actor}=await createDatabase({includeBilling:false});
 try{
  await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/202610280002_archive_shipments.sql','utf8'));
  await actor(1);
  const fake=(await db.query("select public.urgent_publish_test_shipment('Test visibilité','Test visibilité',now()+interval '7 days','VL / fourgon',1,100,'Test','owner@example.com','Contact privé')as id")).rows[0].id;
  const count=async table=>Number((await db.query(`select count(*)as n from public.${table} where ${table==='urgent_shipments'?'id':'shipment_id'}=$1`,[fake])).rows[0].n);
  // Un exercice ouvert reste une annonce accessible aux transporteurs connectés,
  // sans communiquer ses coordonnées privées aux entreprises non participantes.
  for(const n of [3,4]){
   await actor(n);assert.equal(await count('urgent_shipments'),1);
   assert.equal(await count('urgent_shipment_private'),0);
   await assert.rejects(db.query('select public.urgent_archive_shipment($1,true)',[fake]),/propriétaire/);
  }
  // État de fin de mission installé par la fixture, sans simuler une vraie livraison.
  await db.exec('reset role');
  await db.query("update public.urgent_shipments set status='completed',assigned_company_id=$2 where id=$1",[fake,uid(3)]);
  await actor(4);assert.equal(await count('urgent_shipments'),0);assert.equal(await count('urgent_shipment_private'),0);
  await actor(3);assert.equal(await count('urgent_shipments'),1);assert.equal(await count('urgent_shipment_private'),1);
  await assert.rejects(db.query('select public.urgent_archive_shipment($1,true)',[fake]),/propriétaire/);
  await actor(1);await db.query('select public.urgent_archive_shipment($1,true)',[fake]);
  assert.equal((await db.query('select archived_at is not null as archived,status from public.urgent_shipments where id=$1',[fake])).rows[0].status,'completed');
  await actor(4);assert.equal(await count('urgent_shipments'),0);
  await actor(3);assert.equal(await count('urgent_shipments'),1);
  assert.equal((await db.query('select archived_at is not null as archived from public.urgent_shipments where id=$1',[fake])).rows[0].archived,true);
  console.log('PASS visibilité : exercice ouvert accessible sans contact privé, exercice terminé invisible aux autres transporteurs, suivi conservé pour le transporteur attribué, rangement réservé au propriétaire et historique conservé.');
 }finally{await db.close();}
})().catch(e=>{console.error(e);process.exit(1)});

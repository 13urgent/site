// Rollout against the exact one-query activation pack, with synthetic companies.
const {createDatabase}=require('./helpers/pilot-database.cjs');
const fs=require('fs'),assert=require('assert/strict');
(async()=>{
 for(const logoAlreadyInstalled of [false,true]){
 const {db,actor,uid}=await createDatabase({includeBilling:false});
 try{
  await db.exec(`create schema storage;create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,owner_id text,metadata jsonb);alter table auth.users add column email_confirmed_at timestamptz;update auth.users set email_confirmed_at=now();`);
  for(const name of ['202610280001_edit_shipments.sql','202610280002_archive_shipments.sql','202610290002_mobile_missions.sql','202610300001_shipment_schedule.sql','202610300002_platform_services.sql','202610310001_transport_dossier.sql',...(logoAlreadyInstalled?['202610310006_shipper_logo.sql']:[])])await db.exec(fs.readFileSync(__dirname+'/../supabase/migrations/'+name,'utf8'));
  const pack=fs.readFileSync(__dirname+'/../supabase/setup/open-transport-documents.sql','utf8');
  await db.exec(pack);await db.exec(pack);
  assert.equal((await db.query('select public.urgent_transport_dossier_policy() p')).rows[0].p.rollout,'authorized_companies');
  const enabled=async n=>{await actor(n);return(await db.query('select public.urgent_document_prepare_enabled() e')).rows[0].e};
  assert.equal(await enabled(2),true);assert.equal(await enabled(3),true);
  assert.equal((await db.query('select count(*)::int n from public.urgent_transport_document_access')).rows[0].n,0,'No per-company pilot grant required');
  await actor(2);await db.query('select public.urgent_save_document_branding(0,$1)',[{address:'Adresse fictive du client'}]);
  const shipment=(await db.query("select public.urgent_publish_shipment('Ville A','Ville B',now()+interval'7 days','Porteur',1,500,'Client fictif','test@example.com','Marchandise fictive')id")).rows[0].id;
  await actor(3);const offer=(await db.query('select public.urgent_submit_offer($1,450)id',[shipment])).rows[0].id;
  await actor(2);await db.query('select public.urgent_accept_offer($1,true,450)',[offer]);
  const data={consignor_name:'Expéditeur fictif',consignor_address:'1 rue fictive, Ville A',consignee_name:'Destinataire fictif',consignee_address:'2 rue fictive, Ville B',goods_description:'Marchandise fictive',pallets:1,weight_kg:500};
  const save=(id,kind,version,values=data)=>db.query('select public.urgent_save_transport_document($1,$2,$3,$4,$5,$6,true)',[uid(id),shipment,kind,version,kind==='confirmation'?'issued':'draft',values]);
  await save(81,'confirmation',0);await save(82,'waybill',0);
  await db.query('select public.urgent_share_transport_documents($1,$2,$3,$4)',[uid(83),shipment,uid(81),uid(82)]);
  await actor(3);await save(84,'waybill',1,{...data,driver_name:'Conducteur fictif',vehicle_plate:'AA-000-AA',weight_kg:550});
  assert.equal((await db.query('select public.urgent_transport_document($1)d',[uid(84)])).rows[0].d.snapshot.data.weight_kg,550);
  await assert.rejects(save(85,'confirmation',1),/émettrice/);
  await actor(4);await assert.rejects(db.query('select public.urgent_transport_document($1)',[uid(84)]),/parties/);
  await assert.rejects(db.query('select public.urgent_review_transport_document_access($1,true)',[uid(4)]),/Administration/);
  await db.exec('reset role');await db.query('update public.urgent_business_access set pilot_enabled=false where company_id=$1',[uid(4)]);
  assert.equal(await enabled(4),false);
  await actor(1);await db.query('select public.urgent_review_transport_document_access($1,true)',[uid(4)]);
  assert.equal(await enabled(4),false,'A documentary grant cannot authorize an unvalidated company');
  await db.exec('reset role');await db.query('update public.urgent_business_access set pilot_enabled=true where company_id=$1',[uid(4)]);
  assert.equal(await enabled(4),true,'A newly validated company gains access automatically');
  await db.exec('reset role');await db.query('update auth.users set email_confirmed_at=null where id=$1',[uid(4)]);
  assert.equal(await enabled(4),false);
  await actor(1);await db.query('select public.urgent_review_transport_document_access($1,false)',[uid(3)]);
  assert.equal(await enabled(3),false);await assert.rejects(save(85,'waybill',2),/indisponible/);
  assert.equal((await db.query('select public.urgent_transport_document($1)d',[uid(82)])).rows[0].d.id,uid(82),'Recipient printing remains possible after document access suspension');
  await db.exec('reset role');await db.exec(pack);
  assert.equal(await enabled(3),false,'Replaying activation preserves an explicit suspension');
  await actor(1);await db.query('select public.urgent_review_transport_document_access($1,true)',[uid(3)]);
  assert.equal(await enabled(3),true);await save(85,'waybill',2);
  await db.exec('reset role');
  const next=uid(5);await db.query('insert into auth.users(id,email,email_confirmed_at)values($1,$2,now())',[next,'future@example.com']);await db.query('insert into public.companies values($1,$2)',[next,'Future entreprise fictive']);await db.query("insert into public.profiles values($1,$1,'carrier')",[next]);
  assert.equal(await enabled(5),false);
  await db.exec('reset role');await db.query("insert into public.urgent_business_access(company_id,siret,registry_checked,pilot_enabled,plan,reviewed_by)values($1,'91871039300052',true,true,'basics',$2)",[next,uid(1)]);
  assert.equal(await enabled(5),true,'Companies registered after deployment need no pilot grant');
  await db.exec("reset role;select set_config('request.jwt.claim.sub','',false);set role anon");
  await assert.rejects(db.query('select public.urgent_document_prepare_enabled()'),/permission denied/);
  await assert.rejects(db.query('select * from public.urgent_transport_documents'),/permission denied/);
  console.log('PASS ouverture : pack rejouable depuis état réel, entreprises validées actuelles et futures, e-mail confirmé, suspensions conservées, attribution/confirmation/lettre/partage/modification transporteur, cloisonnement et lecture conservée.');
 }finally{await db.close()}
 }
})().catch(e=>{console.error(e);process.exit(1)});

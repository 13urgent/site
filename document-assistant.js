'use strict';
// Précontrôles locaux uniquement : aucune approbation, aucun transfert de document.
(()=>{
 const labels={registration:'Immatriculation / Kbis',transport_licence:'Licence de transport',insurance_rc:'Assurance responsabilité civile',insurance_goods:'Assurance marchandises transportées'};
 const formats={
  'application/pdf':{extensions:['pdf'],label:'PDF',signature:[0x25,0x50,0x44,0x46,0x2d]},
  'image/jpeg':{extensions:['jpg','jpeg'],label:'JPEG',signature:[0xff,0xd8,0xff]},
  'image/png':{extensions:['png'],label:'PNG',signature:[0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]}
 };
 const maxSize=10*1024*1024;
 function today(){
  const values={};for(const p of new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()))values[p.type]=p.value;
  return values.year+'-'+values.month+'-'+values.day;
 }
 function validDate(value){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const [year,month,day]=value.split('-').map(Number);if(year<1000||month<1||month>12||day<1||day>31)return false;
  const d=new Date(Date.UTC(year,month-1,day));return d.getUTCFullYear()===year&&d.getUTCMonth()===month-1&&d.getUTCDate()===day;
 }
 function expiryIssue(kind,expiry){
  if(!expiry)return kind==='registration'?null:'Renseignez la date de fin de validité figurant sur la licence ou l’assurance.';
  if(!validDate(expiry))return 'La date de fin de validité est invalide.';
  if(expiry<today())return 'La date de fin de validité est passée. Déposez une pièce à jour.';
  return null;
 }
 function result(issues,checks){return {ok:issues.length===0,issues,checks,message:issues.length?issues.join(' '):'Précontrôles techniques réussis. Le contenu, l’identité de l’entreprise et les garanties restent à vérifier par 13 URGENT. Ce contrôle ne vaut pas approbation du document.'};}
 async function inspectFile(file,{kind,expiry=''}={}){
  const issues=[],checks=[];
  if(!Object.hasOwn(labels,kind))issues.push('Choisissez une catégorie de justificatif prise en charge.');
  else{const problem=expiryIssue(kind,expiry);if(problem)issues.push(problem);else if(expiry)checks.push('Date déclarée non expirée à la date de Paris.');}
  if(!(file instanceof Blob)||typeof file.name!=='string'){issues.push('Choisissez un fichier PDF, JPG ou PNG.');return result(issues,checks);}
  if(file.size===0){issues.push('Le fichier est vide. Choisissez un document contenant vos justificatifs.');return result(issues,checks);}
  if(file.size>maxSize){issues.push('Le fichier dépasse 10 Mo. Réduisez sa taille avant de l’envoyer.');return result(issues,checks);}
  checks.push('Fichier non vide et inférieur ou égal à 10 Mo.');
  const mime=file.type.toLowerCase(),format=Object.hasOwn(formats,mime)?formats[mime]:null;
  if(!format){issues.push('Format non pris en charge : seuls PDF, JPG et PNG sont autorisés.');return result(issues,checks);}
  const filename=file.name.toLowerCase(),extension=filename.split('.').pop();
  if(!format.extensions.includes(extension))issues.push('L’extension du fichier ne correspond pas au format annoncé. Exportez-le à nouveau en PDF, JPG ou PNG.');
  if(/\.(?:exe|com|bat|cmd|ps1|vbs|vbe|js|jse|msi|scr|html?|svg)(?:\.|$)/i.test(filename))issues.push('Le nom du fichier contient une extension non autorisée. Utilisez un document PDF, JPG ou PNG sans extension exécutable.');
  let header;
  try{header=new Uint8Array(await file.slice(0,20).arrayBuffer());}
  catch{issues.push('Le fichier ne peut pas être lu. Sélectionnez-le à nouveau.');return result(issues,checks);}
  const signatureOk=format.signature.every((byte,index)=>header[index]===byte);
  if(!signatureOk){issues.push('Le contenu du fichier ne correspond pas au format annoncé. Choisissez le document original ou exportez-le à nouveau.');return result(issues,checks);}
  checks.push('En-tête '+format.label+' cohérent avec le format annoncé.');
  if(file.type.toLowerCase().startsWith('image/')){
   if(typeof createImageBitmap==='function'){
    let bitmap;
    try{bitmap=await createImageBitmap(file,{resizeWidth:32,resizeHeight:32});if(!bitmap.width||!bitmap.height)throw Error('Image vide');checks.push('Image décodable par le navigateur.');}
    catch{issues.push('L’image ne peut pas être ouverte. Exportez une image lisible en JPG ou PNG.');}
    finally{bitmap?.close();}
   }else checks.push('En-tête d’image contrôlé ; décodage indisponible dans ce navigateur.');
  }
  return result(issues,checks);
 }
 function analyseChecklist(rows){
  const issues=[],checks=[],items=[];const source=Array.isArray(rows)?rows:[];
  for(const[kind,label]of Object.entries(labels)){
   const matches=source.filter(row=>row&&row.document_type===kind);const row=matches[0];let reason=row?.reason||'missing',message;
   if(matches.length>1){reason='unknown';message='Plusieurs résultats ont été reçus. Actualisez le dossier pour vérifier la dernière pièce.';}
   else if(reason==='missing')message='Pièce manquante : déposez ce justificatif.';
   else if(reason==='not_approved')message=row?.review_status==='rejected'?'Pièce refusée : contactez 13 URGENT pour connaître la correction attendue.':'Pièce en attente de vérification par 13 URGENT.';
   else if(reason==='expiry_missing')message='Date de fin de validité manquante : vérifiez la date figurant sur le document.';
   else if(reason==='expired')message='Pièce expirée : déposez un justificatif à jour.';
   else if(reason==='valid'&&row?.review_status==='approved'){
    const problem=expiryIssue(kind,row.expires_on||'');
    if(problem){reason=validDate(row.expires_on)&&row.expires_on<today()?'expired':'expiry_missing';message=problem;}
    else message='Pièce approuvée et date déclarée valide.';
   }else{reason='unknown';message='État de vérification incomplet : actualisez le dossier ou contactez 13 URGENT.';}
   const ok=reason==='valid';items.push({kind,label,ok,reason,message});(ok?checks:issues).push(label+' : '+message);
  }
  return {ok:issues.length===0,issues,checks,items,message:issues.length?'Votre dossier nécessite encore des vérifications ou des pièces à jour.':'Les quatre catégories disposent de pièces approuvées. Les droits d’accès dépendent aussi de la validation de l’établissement et de votre abonnement.'};
 }
 window.urgentDocumentAssistant=Object.freeze({inspectFile,analyseChecklist});
})();

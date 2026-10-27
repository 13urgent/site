"use strict";
const accountDialog=document.getElementById('accountDialog');
const authNotice=document.getElementById('authNotice');
const authLinkExpired=[location.search.slice(1),location.hash.slice(1)].some(value=>new URLSearchParams(value).get('error_code')==='otp_expired');
const configured=Boolean(window.URGENT_SUPABASE_URL&&window.URGENT_SUPABASE_PUBLISHABLE_KEY&&window.supabase);
window.URGENT_SUPABASE_CONFIGURED=configured;
const sb=configured?window.supabase.createClient(window.URGENT_SUPABASE_URL,window.URGENT_SUPABASE_PUBLISHABLE_KEY):null;
function notify(msg){authNotice.hidden=false;authNotice.textContent=msg;}
let authOperationPending=false;
let authView=0;
let passwordRecoveryUser=null;
async function runAuthOperation(operation,errorMessage){
 if(authOperationPending)return;
 authOperationPending=true;
 const controls=['signUp','signIn','signOut','magicLink','savePassword','saveSubscription'].map(id=>document.getElementById(id)).filter(Boolean);
 const disabled=controls.map(control=>control.disabled);
 controls.forEach(control=>control.disabled=true);accountDialog.setAttribute('aria-busy','true');
 try{await operation();}catch{notify(errorMessage);}finally{
  controls.forEach((control,index)=>control.disabled=disabled[index]);
  accountDialog.removeAttribute('aria-busy');authOperationPending=false;
 }
}
document.getElementById('openAccount').addEventListener('click',()=>{authNotice.hidden=true;accountDialog.showModal();updateAuth().catch(()=>notify('Impossible de vérifier la session.'));});
document.getElementById('closeAccount').addEventListener('click',()=>accountDialog.close());
async function updateAuth(){
 const view=++authView;
 const result=sb?await sb.auth.getUser():{data:{user:null}};
 if(view!==authView)return;
 const user=result.data?.user||null;
 document.getElementById('signOut').hidden=!user;
 document.getElementById('openAccount').textContent=user?'Mon compte':'Connexion / Inscription';
 accountDialog.querySelector('h2').textContent=user?'Mon compte':'Connexion / inscription';
 for(const id of ['authEmail','authPassword','accountType'])document.getElementById(id).closest('label').hidden=Boolean(user);
 for(const id of ['signUp','signIn'])document.getElementById(id).hidden=Boolean(user);
 for(const id of ['registrationAction','loginActions']){const group=document.getElementById(id);if(group)group.hidden=Boolean(user)||(id==='registrationAction'&&window.URGENT_ALLOW_REGISTRATION===false);}
 if(window.URGENT_ALLOW_REGISTRATION===false){document.getElementById('signUp').hidden=true;document.getElementById('accountType').closest('label').hidden=true;}
 document.getElementById('passwordSettings').hidden=!user||passwordRecoveryUser!==user.id;
 document.getElementById('magicLink').hidden=Boolean(user&&passwordRecoveryUser===user.id);
 if(user?.email)document.getElementById('authEmail').value=user.email;
 document.getElementById('businessRegistration').hidden=Boolean(user)||window.URGENT_ALLOW_REGISTRATION===false;
 document.getElementById('accountIdentity').textContent=user?.email||'';
 await updateSubscriptionRequest(user);
}
async function action(kind){if(kind==='signup'&&window.URGENT_ALLOW_REGISTRATION===false){notify('Les inscriptions publiques ne sont pas ouvertes sur ce pilote.');return;}if(!sb){notify('Connexion Supabase non configurée. Renseignez config.js avec URL et clé publique.');return;}
 const email=document.getElementById('authEmail').value.trim();const password=document.getElementById('authPassword').value;
 if(!email||password.length<8){notify('Saisissez un e-mail valide et un mot de passe de 8 caractères minimum.');return;}
 let res;
 if(kind==='signup'){
  const company=document.getElementById('businessName').value.trim();
  const siret=document.getElementById('businessSiret').value.trim();
  if(!company||!/^\d{14}$/.test(siret)||!document.getElementById('businessUse').checked){notify('Pour vous inscrire, renseignez la raison sociale, un SIRET de 14 chiffres et confirmez l’usage professionnel.');return;}
  // Déclarations utilisateur uniquement : aucun rôle ni statut vérifié attribué ici.
  const requestedType=document.getElementById('accountType').value;
  const plan=requestedType==='carrier'?selectedPlan():null;
  if(requestedType==='carrier'&&!plan){notify('Choisissez un forfait transporteur pour votre demande.');return;}
  res=await sb.auth.signUp({email,password,options:{data:{requested_account_type:document.getElementById('accountType').value,account_type:document.getElementById('accountType').value,company_name:company,business_name:company,business_siret:siret,business_use_declared:true,business_declaration_version:'2026-10-17',...(plan?{subscription_plan_request:plan,subscription_catalog_version:'2026-10-17'}:{})}}});
 }else{res=await sb.auth.signInWithPassword({email,password});}
 if(res.error){notify('Erreur : '+res.error.message);return;}
 notify(kind==='signup'?'Inscription enregistrée. Vérifiez votre boîte e-mail si la confirmation est activée. Connectez-vous après confirmation pour consulter les fonctions disponibles pour votre profil.':'Connexion réussie. Les fonctions disponibles dépendent de votre rôle et de la validation de votre établissement. Pour les transporteurs, les propositions nécessitent aussi des documents valides et des droits d’accès en cours.');
 try{await updateAuth();if(window.refreshProfessionalAccess)await window.refreshProfessionalAccess();}
 catch{notify(kind==='signup'?'Inscription enregistrée, mais votre espace ne peut pas être actualisé. Actualisez la page avant de réessayer.':'Connexion effectuée, mais votre espace ne peut pas être actualisé. Actualisez la page.');}
}
document.getElementById('signUp').addEventListener('click',()=>runAuthOperation(()=>action('signup'),'Connexion au service impossible. Réessayez plus tard.'));
document.getElementById('signIn').addEventListener('click',()=>runAuthOperation(()=>action('signin'),'Connexion au service impossible. Réessayez plus tard.'));
document.getElementById('signOut').addEventListener('click',()=>runAuthOperation(async()=>{
 try{if(!sb)return;const {error}=await sb.auth.signOut();if(error)throw error;
 document.getElementById('authPassword').value='';document.getElementById('newPassword').value='';document.getElementById('confirmPassword').value='';
 await updateAuth();notify('Vous êtes déconnecté.');if(window.refreshProfessionalAccess)await window.refreshProfessionalAccess();
 }catch{notify('Déconnexion non confirmée. Réessayez.');}
},'Déconnexion non confirmée. Réessayez.'));


// Conserve le sous-dossier d’hébergement, sans recopier les jetons de l’URL.
function authReturnUrl(){const target=new URL('.',location.href);return target.pathname==='/'?target.origin:target.href;}
// Réinitialisation par e-mail ; aucun compte n’est créé par cette action.
document.getElementById('magicLink').addEventListener('click',()=>runAuthOperation(async()=>{
 const input=document.getElementById('authEmail');if(!input.reportValidity())return;
 if(!sb){notify('Service momentanément indisponible.');return;}
 try{
  const {error}=await sb.auth.resetPasswordForEmail(input.value.trim(),{redirectTo:authReturnUrl()});
  if(error){notify(error.status===429||['over_email_send_rate_limit','over_request_rate_limit'].includes(error.code)?'Trop de demandes. Patientez quelques minutes avant de réessayer.':'Le lien de réinitialisation n’a pas pu être envoyé. Réessayez plus tard ou contactez contact@13urgent.fr.');return;}
  notify('Si un compte correspond à cette adresse, vous recevrez un e-mail pour réinitialiser votre mot de passe. Consultez aussi vos courriers indésirables et ouvrez le lien le plus récent.');
 }catch{notify('Service inaccessible. Aucun envoi ne peut être confirmé.');}
},'Service inaccessible. Aucun envoi ne peut être confirmé.'));

// Un mot de passe ne peut être défini que pour la session authentifiée courante.
const passwordSettings=document.createElement('section');passwordSettings.id='passwordSettings';passwordSettings.hidden=true;
const accountIdentity=document.createElement('p');accountIdentity.id='accountIdentity';authNotice.before(accountIdentity);
accountIdentity.after(document.getElementById('magicLink'));
passwordSettings.innerHTML='<h3>Réinitialiser mon mot de passe</h3><p>Choisissez votre nouveau mot de passe.</p><label>Nouveau mot de passe<input id="newPassword" type="password" minlength="12" autocomplete="new-password"></label><label>Confirmer le mot de passe<input id="confirmPassword" type="password" minlength="12" autocomplete="new-password"></label><button id="savePassword" class="btn primary" type="button">Enregistrer mon mot de passe</button>';
authNotice.before(passwordSettings);
document.getElementById('savePassword').addEventListener('click',()=>runAuthOperation(async()=>{
 const recoveryUser=passwordRecoveryUser;
 if(!recoveryUser){notify('Utilisez « Mot de passe oublié ? » et ouvrez le lien reçu par e-mail.');return;}
 const field=document.getElementById('newPassword'), confirmation=document.getElementById('confirmPassword');
 if(field.value.length<12){notify('Choisissez au moins 12 caractères.');return;}
 if(field.value!==confirmation.value){notify('Les deux mots de passe doivent être identiques.');return;}
 try{
  if(!sb)throw Error('Service indisponible.');const {data,error}=await sb.auth.getUser();
  if(error||data?.user?.id!==recoveryUser||passwordRecoveryUser!==recoveryUser){notify('Le lien a expiré ou la session a changé. Demandez un nouveau lien de réinitialisation.');return;}
  const result=await sb.auth.updateUser({password:field.value});if(result.error){notify('Modification refusée : '+result.error.message);return;}
  passwordRecoveryUser=null;passwordSettings.hidden=true;field.value='';confirmation.value='';notify('Mot de passe enregistré. Vous pourrez vous connecter avec votre e-mail et ce mot de passe.');
 }catch{notify('Modification non confirmée. Le service est inaccessible.');}
},'Modification non confirmée. Le service est inaccessible.'));
// Choix déclaratif uniquement : ne confère ni abonnement actif ni validation entreprise.
const subscriptionPlans=[
 {id:'basics',name:'Start',price:'Gratuit',limit:'1 transport par mois'},
 {id:'bronze',name:'Drive',price:'12,50 € HT / mois',limit:'5 transports par mois'},
 {id:'silver',name:'Boost',price:'33,33 € HT / mois',limit:'30 transports par mois'},
 {id:'gold',name:'Premium',price:'62,50 € HT / mois',limit:'Transports illimités'}
];
const subscriptionRequest=document.createElement('fieldset');subscriptionRequest.id='subscriptionRequest';subscriptionRequest.hidden=true;
const subscriptionLegend=document.createElement('legend');subscriptionLegend.textContent='Demande d’abonnement transporteur';subscriptionRequest.append(subscriptionLegend);
for(const plan of subscriptionPlans){
 const label=document.createElement('label');label.className='subscription-choice';
 const radio=document.createElement('input');radio.type='radio';radio.name='requestedSubscription';radio.value=plan.id;
 const description=document.createElement('span');description.textContent=`${plan.name} — ${plan.price} · ${plan.limit}`;
 label.append(radio,description);subscriptionRequest.append(label);
}
const subscriptionInfo=document.createElement('p');subscriptionInfo.className='muted';subscriptionInfo.textContent='Demande de forfait à examiner par CHRONOSS. Pour le service commercial, CHRONOSS confirme le prix et transmet son RIB ; la période est activée après vérification du crédit bancaire effectif et du dossier. Aucun prélèvement automatique. Le pilote gratuit ne demande aucun paiement. Tout abonnement, même payé, ne dispense pas de fournir des documents professionnels valides et à jour. L’accès aux offres reste soumis à la validation du dossier par 13 URGENT et pourra être suspendu si les justificatifs expirent ou deviennent non conformes. Les conditions de suspension, de résiliation, de remboursement et de décompte des transports seront communiquées avant toute souscription.';subscriptionRequest.append(subscriptionInfo);
const saveSubscription=document.createElement('button');saveSubscription.id='saveSubscription';saveSubscription.type='button';saveSubscription.className='btn primary';saveSubscription.textContent='Enregistrer ma demande de forfait';saveSubscription.hidden=true;subscriptionRequest.append(saveSubscription);
passwordSettings.before(subscriptionRequest);
function selectedPlan(){const value=subscriptionRequest.querySelector('input:checked')?.value;return subscriptionPlans.some(p=>p.id===value)?value:null;}
let subscriptionView=0;
async function updateSubscriptionRequest(user){
 const view=++subscriptionView;subscriptionRequest.hidden=true;saveSubscription.hidden=true;
 subscriptionRequest.querySelectorAll('input').forEach(input=>input.checked=false);
 if(!user){subscriptionRequest.hidden=window.URGENT_ALLOW_REGISTRATION===false||document.getElementById('accountType').value!=='carrier';return;}
 const result=await sb.from('profiles').select('role').eq('id',user.id).maybeSingle();
 if(view!==subscriptionView||result.error||result.data?.role!=='carrier')return;
 subscriptionRequest.hidden=false;saveSubscription.hidden=false;
 const previous=user.user_metadata?.subscription_plan_request;
 subscriptionRequest.querySelectorAll('input').forEach(input=>input.checked=input.value===previous);
}
document.getElementById('accountType').addEventListener('change',()=>{updateAuth().catch(()=>notify('Impossible de vérifier la session.'));});
saveSubscription.addEventListener('click',()=>runAuthOperation(async()=>{
 const plan=selectedPlan();if(!plan){notify('Choisissez un forfait.');return;}
 try{
  const current=await sb.auth.getUser();if(current.error||!current.data?.user)throw Error('Session requise.');
  const profile=await sb.from('profiles').select('role').eq('id',current.data.user.id).maybeSingle();
  if(profile.error||profile.data?.role!=='carrier')throw Error('Compte transporteur requis.');
  const result=await sb.auth.updateUser({data:{subscription_plan_request:plan,subscription_catalog_version:'2026-10-17',subscription_requested_at:new Date().toISOString()}});
  if(result.error)throw result.error;
  notify('Choix enregistré dans votre compte. Aucun paiement effectué ; votre abonnement et votre dossier ne sont pas activés.');
 }catch{notify('Demande non confirmée. Vérifiez votre connexion et réessayez.');}
},'Demande non confirmée. Vérifiez votre connexion et réessayez.'));
if(sb)sb.auth.onAuthStateChange((event,session)=>{
 if(event==='PASSWORD_RECOVERY'){passwordRecoveryUser=session?.user?.id||null;accountDialog.showModal();}
 else if(event==='SIGNED_OUT'||event==='SIGNED_IN'){passwordRecoveryUser=null;}
 authView++;setTimeout(()=>{document.getElementById('newPassword').value='';document.getElementById('confirmPassword').value='';updateAuth().catch(()=>notify('Impossible de vérifier la session.'));},0);});
updateAuth().then(()=>{if(authLinkExpired){accountDialog.showModal();notify('Ce lien a expiré ou n’est plus valide. Pour réinitialiser votre mot de passe, demandez un nouveau lien avec « Mot de passe oublié ? ». Si vous attendiez une confirmation d’inscription, contactez contact@13urgent.fr.');}}).catch(()=>notify('Le service de connexion est momentanément inaccessible.'));

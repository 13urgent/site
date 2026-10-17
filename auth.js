"use strict";
const accountDialog=document.getElementById('accountDialog');
const authNotice=document.getElementById('authNotice');
const configured=Boolean(window.URGENT_SUPABASE_URL&&window.URGENT_SUPABASE_PUBLISHABLE_KEY&&window.supabase);
window.URGENT_SUPABASE_CONFIGURED=configured;
const sb=configured?window.supabase.createClient(window.URGENT_SUPABASE_URL,window.URGENT_SUPABASE_PUBLISHABLE_KEY):null;
function notify(msg){authNotice.hidden=false;authNotice.textContent=msg;}
document.getElementById('openAccount').addEventListener('click',()=>{authNotice.hidden=true;accountDialog.showModal();updateAuth().catch(()=>notify('Impossible de vérifier la session.'));});
document.getElementById('closeAccount').addEventListener('click',()=>accountDialog.close());
async function updateAuth(){
 const result=sb?await sb.auth.getUser():{data:{user:null}};
 const user=result.data?.user||null;
 document.getElementById('signOut').hidden=!user;
 document.getElementById('openAccount').textContent=user?'Mon compte':'Connexion / Inscription';
 accountDialog.querySelector('h2').textContent=user?'Mon compte':'Connexion / inscription';
 for(const id of ['authEmail','authPassword','accountType'])document.getElementById(id).closest('label').hidden=Boolean(user);
 for(const id of ['signUp','signIn','magicLink'])document.getElementById(id).hidden=Boolean(user);
 document.getElementById('passwordSettings').hidden=!user;
 document.getElementById('businessRegistration').hidden=Boolean(user);
 document.getElementById('accountIdentity').textContent=user?.email||'';
 await updateSubscriptionRequest(user);
}
async function action(kind){if(!sb){notify('Connexion Supabase non configurée. Renseignez config.js avec URL et clé publique.');return;}
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
 notify(kind==='signup'?'Inscription enregistrée. Vérifiez votre boîte e-mail si la confirmation est activée. Connectez-vous après confirmation pour consulter les fonctions disponibles pour votre profil.':'Connexion réussie. Les transporteurs disposant d’un profil entreprise peuvent accéder à leurs documents. Les offres en ligne ne sont pas encore activées.');await updateAuth();if(window.refreshProfessionalAccess)await window.refreshProfessionalAccess();
}
document.getElementById('signUp').addEventListener('click',()=>action('signup').catch(()=>notify('Connexion au service impossible. Réessayez plus tard.')));
document.getElementById('signIn').addEventListener('click',()=>action('signin').catch(()=>notify('Connexion au service impossible. Réessayez plus tard.')));
document.getElementById('signOut').addEventListener('click',async()=>{
 try{if(!sb)return;const {error}=await sb.auth.signOut();if(error)throw error;
 document.getElementById('authPassword').value='';document.getElementById('newPassword').value='';document.getElementById('confirmPassword').value='';
 await updateAuth();notify('Vous êtes déconnecté.');if(window.refreshProfessionalAccess)await window.refreshProfessionalAccess();
 }catch{notify('Déconnexion non confirmée. Réessayez.');}
});


// Le lien ouvre la même origine HTTP(S) que celle utilisée pour la demande.
document.getElementById('magicLink').addEventListener('click',async event=>{
 const emailInput=document.getElementById('authEmail');
 if(!emailInput.reportValidity())return;
 if(!sb){notify('Service de connexion indisponible.');return;}
 if(!['http:','https:'].includes(location.protocol)){notify('Ouvrez le site avec le serveur local HTTP ou son adresse HTTPS.');return;}
 const button=event.currentTarget;button.disabled=true;
 try{
  const {error}=await sb.auth.signInWithOtp({email:emailInput.value.trim(),options:{shouldCreateUser:false,emailRedirectTo:location.origin}});
  if(error){notify('Envoi impossible : '+error.message);return;}
  notify('Si ce compte peut se connecter, un lien vient d’être envoyé. Ouvrez le dernier e-mail dans ce navigateur et gardez le serveur local lancé.');
 }catch{notify('Service inaccessible. Aucun envoi ne peut être confirmé.');}finally{button.disabled=false;}
});

// Un mot de passe ne peut être défini que pour la session authentifiée courante.
const passwordSettings=document.createElement('section');passwordSettings.id='passwordSettings';passwordSettings.hidden=true;
passwordSettings.innerHTML='<p id="accountIdentity"></p><h3>Définir mon mot de passe</h3><p>Choisissez un mot de passe personnel pour vos prochaines connexions.</p><label>Nouveau mot de passe<input id="newPassword" type="password" minlength="12" autocomplete="new-password"></label><label>Confirmer le mot de passe<input id="confirmPassword" type="password" minlength="12" autocomplete="new-password"></label><button id="savePassword" class="btn primary" type="button">Enregistrer mon mot de passe</button>';
authNotice.before(passwordSettings);
document.getElementById('savePassword').addEventListener('click',async event=>{
 const field=document.getElementById('newPassword'), confirmation=document.getElementById('confirmPassword');
 if(field.value.length<12){notify('Choisissez au moins 12 caractères.');return;}
 if(field.value!==confirmation.value){notify('Les deux mots de passe doivent être identiques.');return;}
 const button=event.currentTarget;button.disabled=true;
 try{
  if(!sb)throw Error('Service indisponible.');const {data,error}=await sb.auth.getUser();
  if(error||!data?.user){notify('Reconnectez-vous avant de définir votre mot de passe.');return;}
  const result=await sb.auth.updateUser({password:field.value});if(result.error){notify('Modification refusée : '+result.error.message);return;}
  field.value='';confirmation.value='';notify('Mot de passe enregistré. Vous pourrez vous connecter avec votre e-mail et ce mot de passe.');
 }catch{notify('Modification non confirmée. Le service est inaccessible.');}finally{button.disabled=false;}
});
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
const subscriptionInfo=document.createElement('p');subscriptionInfo.className='muted';subscriptionInfo.textContent='Demande sans paiement pour le moment. Tout abonnement, même payé, ne dispense pas de fournir des documents professionnels valides et à jour. L’accès aux offres reste soumis à la validation du dossier par 13 URGENT et pourra être suspendu si les justificatifs expirent ou deviennent non conformes. Les conditions de suspension, de résiliation, de remboursement et de décompte des transports seront communiquées avant toute souscription.';subscriptionRequest.append(subscriptionInfo);
const saveSubscription=document.createElement('button');saveSubscription.type='button';saveSubscription.className='btn primary';saveSubscription.textContent='Enregistrer ma demande de forfait';saveSubscription.hidden=true;subscriptionRequest.append(saveSubscription);
passwordSettings.before(subscriptionRequest);
function selectedPlan(){const value=subscriptionRequest.querySelector('input:checked')?.value;return subscriptionPlans.some(p=>p.id===value)?value:null;}
let subscriptionView=0;
async function updateSubscriptionRequest(user){
 const view=++subscriptionView;subscriptionRequest.hidden=true;saveSubscription.hidden=true;
 subscriptionRequest.querySelectorAll('input').forEach(input=>input.checked=false);
 if(!user){subscriptionRequest.hidden=document.getElementById('accountType').value!=='carrier';return;}
 const result=await sb.from('profiles').select('role').eq('id',user.id).maybeSingle();
 if(view!==subscriptionView||result.error||result.data?.role!=='carrier')return;
 subscriptionRequest.hidden=false;saveSubscription.hidden=false;
 const previous=user.user_metadata?.subscription_plan_request;
 subscriptionRequest.querySelectorAll('input').forEach(input=>input.checked=input.value===previous);
}
document.getElementById('accountType').addEventListener('change',()=>{updateAuth().catch(()=>notify('Impossible de vérifier la session.'));});
saveSubscription.addEventListener('click',async()=>{
 const plan=selectedPlan();if(!plan){notify('Choisissez un forfait.');return;}saveSubscription.disabled=true;
 try{
  const current=await sb.auth.getUser();if(current.error||!current.data?.user)throw Error('Session requise.');
  const profile=await sb.from('profiles').select('role').eq('id',current.data.user.id).maybeSingle();
  if(profile.error||profile.data?.role!=='carrier')throw Error('Compte transporteur requis.');
  const result=await sb.auth.updateUser({data:{subscription_plan_request:plan,subscription_catalog_version:'2026-10-17',subscription_requested_at:new Date().toISOString()}});
  if(result.error)throw result.error;
  notify('Choix enregistré dans votre compte. Aucun paiement effectué ; votre abonnement et votre dossier ne sont pas activés.');
 }catch{notify('Demande non confirmée. Vérifiez votre connexion et réessayez.');}finally{saveSubscription.disabled=false;}
});
if(sb)sb.auth.onAuthStateChange(()=>{setTimeout(()=>{document.getElementById('newPassword').value='';document.getElementById('confirmPassword').value='';updateAuth().catch(()=>notify('Impossible de vérifier la session.'));},0);});
updateAuth().catch(()=>notify('Le service de connexion est momentanément inaccessible.'));

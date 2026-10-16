"use strict";
const accountDialog=document.getElementById('accountDialog');
const authNotice=document.getElementById('authNotice');
const configured=Boolean(window.URGENT_SUPABASE_URL&&window.URGENT_SUPABASE_PUBLISHABLE_KEY&&window.supabase);
window.URGENT_SUPABASE_CONFIGURED=configured;
const sb=configured?window.supabase.createClient(window.URGENT_SUPABASE_URL,window.URGENT_SUPABASE_PUBLISHABLE_KEY):null;
function notify(msg){authNotice.hidden=false;authNotice.textContent=msg;}
document.getElementById('openAccount').addEventListener('click',()=>{authNotice.hidden=true;accountDialog.showModal();});
document.getElementById('closeAccount').addEventListener('click',()=>accountDialog.close());
async function updateAuth(){if(!sb)return;const {data}=await sb.auth.getUser();document.getElementById('signOut').hidden=!data?.user;document.getElementById('openAccount').textContent=data?.user?'Mon compte':'Connexion / Inscription';}
async function action(kind){if(!sb){notify('Connexion Supabase non configurée. Renseignez config.js avec URL et clé publique.');return;}
 const email=document.getElementById('authEmail').value.trim();const password=document.getElementById('authPassword').value;
 if(!email||password.length<8){notify('Saisissez un e-mail valide et un mot de passe de 8 caractères minimum.');return;}
 const res=kind==='signup'?await sb.auth.signUp({email,password,options:{data:{requested_account_type:document.getElementById('accountType').value,role:document.getElementById('accountType').value}}}):await sb.auth.signInWithPassword({email,password});
 if(res.error){notify('Erreur : '+res.error.message);return;}
 notify(kind==='signup'?'Inscription enregistrée. Vérifiez votre boîte e-mail si la confirmation est activée. Connectez-vous après confirmation pour consulter les fonctions disponibles pour votre profil.':'Connexion réussie. Les transporteurs disposant d’un profil entreprise peuvent accéder à leurs documents. Les offres en ligne ne sont pas encore activées.');await updateAuth();if(window.refreshProfessionalAccess)await window.refreshProfessionalAccess();
}
document.getElementById('signUp').addEventListener('click',()=>action('signup').catch(()=>notify('Connexion au service impossible. Réessayez plus tard.')));
document.getElementById('signIn').addEventListener('click',()=>action('signin').catch(()=>notify('Connexion au service impossible. Réessayez plus tard.')));
document.getElementById('signOut').addEventListener('click',async()=>{if(sb){await sb.auth.signOut();notify('Vous êtes déconnecté.');await updateAuth();if(window.refreshProfessionalAccess)await window.refreshProfessionalAccess();}});
updateAuth().catch(()=>notify('Le service de connexion est momentanément inaccessible.'));

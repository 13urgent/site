'use strict';
(()=>{
 if(window.URGENT_BILLING_TEST_UI!==true)return;
 const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const section=make('section',undefined,'section panel');section.id='billing-tests';section.append(make('h2','Paiements — environnement de test'),make('p','Essais techniques uniquement. Aucun paiement réel ni abonnement professionnel actif ne sera créé. Un paiement de test ne valide aucun document et ne débloque pas les offres.'));
 const consent=make('label',undefined,'professional-check');const acknowledge=make('input');acknowledge.type='checkbox';acknowledge.id='billingTestAcknowledgement';consent.append(acknowledge,make('span','Je lance un essai en mode test, sans paiement réel ni engagement commercial.'));section.append(consent);
 const notice=make('p');notice.id='billingTestNotice';notice.setAttribute('role','status');section.append(notice);
 const plans=make('select');plans.id='billingTestPlan';for(const[id,text]of [['bronze','Drive — 12,50 € HT / mois'],['silver','Boost — 33,33 € HT / mois'],['gold','Premium — 62,50 € HT / mois']]){const option=make('option',text);option.value=id;plans.append(option);}
 const planLabel=make('label','Forfait à tester');planLabel.append(plans);section.append(planLabel);
 const pay=make('button','Tester cet abonnement','btn secondary');pay.type='button';pay.id='billingTestCheckout';section.append(pay);
 const list=make('div',undefined,'doc-list');section.append(make('h3','Mes commandes de test'),list);document.querySelector('main').append(section);
 let generation=0;
 const statusLabels={created:'Demande créée',checkout_created:'Session de test créée',paid_test:'Paiement de test confirmé par le serveur',expired:'Demande expirée',needs_review:'Vérification manuelle requise',refunded_test:'Remboursement de test enregistré'};
 async function refresh(){const current=++generation;list.replaceChildren();pay.disabled=true;
  try{if(!sb)throw Error('Service indisponible.');const{data,error}=await sb.auth.getUser();if(error||!data?.user){notice.textContent='Connectez-vous à votre compte professionnel.';return;}
   const profile=await sb.from('profiles').select('role').eq('id',data.user.id).single();if(current!==generation)return;pay.disabled=profile.error||profile.data?.role!=='carrier';
   const result=await sb.from('urgent_billing_orders').select('id,kind,plan,amount_ht_cents,status,created_at').order('created_at',{ascending:false}).limit(20);if(result.error)throw result.error;if(current!==generation)return;
   for(const order of result.data){const card=make('article',undefined,'doc-item');card.append(make('strong',order.kind==='subscription'?'Abonnement de test':'Frais de mise en relation de test'),make('span',`${(order.amount_ht_cents/100).toLocaleString('fr-FR',{style:'currency',currency:'EUR'})} HT · ${statusLabels[order.status]||'État à vérifier'}`));list.append(card);}
   if(!result.data.length)list.append(make('p','Aucune commande de test.'));
  }catch{if(current===generation)notice.textContent='Le serveur de paiement de test n’est pas encore configuré ou accessible.';}
 }
 window.urgentStartBillingTest=async choice=>{
  if(!acknowledge.checked){notice.textContent='Confirmez d’abord qu’il s’agit uniquement d’un essai sans paiement réel.';section.scrollIntoView({block:'center'});return;}
  pay.disabled=true;
  try{
   const pending=await sb.from('urgent_billing_orders').select('request_key,kind,plan,offer_id,status,expires_at,stripe_session_id').eq('kind',choice.kind).in('status',['created','checkout_created']).order('created_at',{ascending:false}).limit(10);if(pending.error)throw pending.error;
   const previous=pending.data.find(order=>new Date(order.expires_at).getTime()>Date.now()+(order.stripe_session_id?0:31*60*1000)&&(choice.kind==='subscription'?order.plan===choice.plan:order.offer_id===choice.offerId));
   const result=await sb.functions.invoke('billing-checkout',{body:{...choice,requestKey:previous?.request_key||crypto.randomUUID(),termsVersion:'test-preparation-v1'}});
   if(result.error){let message=result.error.message;try{message=(await result.error.context.json()).error||message;}catch{}throw Error(message);}
   if(result.data?.test!==true||!result.data.url?.startsWith('https://checkout.stripe.com/'))throw Error('Adresse de paiement non conforme.');
   location.assign(result.data.url);
  }catch(e){notice.textContent='Paiement non démarré : '+e.message;pay.disabled=false;}
 };
 pay.onclick=()=>window.urgentStartBillingTest({kind:'subscription',plan:plans.value});
 const refreshButton=make('button','Actualiser les commandes de test','btn secondary');refreshButton.type='button';refreshButton.onclick=refresh;section.append(refreshButton);
 if(new URL(location.href).searchParams.has('billing'))notice.textContent='Retour du prestataire : seul le statut confirmé par le serveur fait foi. L’adresse de retour ne prouve pas le paiement.';
 sb?.auth.onAuthStateChange(()=>{generation++;list.replaceChildren();acknowledge.checked=false;setTimeout(refresh,0);});refresh();
})();

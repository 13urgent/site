#!/usr/bin/env python3
"""One follow-up after seven days, only to an accepted new campaign without reply or stop."""
from datetime import datetime,timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
import hashlib,json,os,re
from pathlib import Path
import commercial_agent as agent
import commercial_hours
import run_campaign
import monitor_replies
import send_service_reply as service


def eligible(state,now):
    suppressed=set(state.get('suppressed_hashes',[]));result=[]
    for cid,rows in state.get('campaigns',{}).items():
        if not cid.startswith('direction-'):continue
        for rid,r in rows.items():
            if r.get('followup_allowed') is not True or r.get('followup_count',0)!=0 or r.get('status')!='accepted_and_archived':continue
            if r.get('response_received_to_qualify') or r.get('opted_out') or r.get('blocked_for_resend') or r.get('delivery_status')=='hard_bounced' or r.get('recipient_fingerprint') in suppressed:continue
            try:due=datetime.fromisoformat(r['followup_due_at']);created=datetime.fromisoformat(r['created_at'])
            except (KeyError,ValueError,TypeError):continue
            if due.utcoffset() is None or created.utcoffset() is None or now<due or (now-created).days>30:continue
            if not re.fullmatch('[0-9a-f]{64}',r.get('fingerprint','')) or not re.fullmatch('[0-9a-f]{64}',r.get('recipient_fingerprint','')):continue
            result.append((cid,rid,r))
    return result[:10]


def original(archive,record):
    mid='<'+record['fingerprint']+'@13urgent.fr>'
    status,data=archive.client.uid('SEARCH',None,'HEADER','Message-ID','"'+mid+'"')
    ids=b' '.join(x for x in data or [] if isinstance(x,bytes)).split()
    if status!='OK' or len(ids)!=1:raise agent.CampaignError('original_sent_message_not_unique')
    status,parts=archive.client.uid('FETCH',ids[0],'(BODY.PEEK[]<0.2000000>)')
    raw=b''.join(x[1] for x in parts or [] if isinstance(x,tuple) and len(x)==2 and isinstance(x[1],bytes))
    if status!='OK' or len(raw)>=2000000:raise agent.CampaignError('original_sent_message_unavailable')
    m=BytesParser(policy=policy.default).parsebytes(raw)
    senders=getaddresses(m.get_all('From',[]));tos=getaddresses(m.get_all('To',[]))
    if str(m.get('Message-ID'))!=mid or len(senders)!=1 or senders[0][1].lower()!=agent.SENDER or len(tos)!=1:raise agent.CampaignError('original_sent_identity_invalid')
    address=tos[0][1]
    if hashlib.sha256(address.lower().encode()).hexdigest()!=record['recipient_fingerprint']:raise agent.CampaignError('original_sent_recipient_mismatch')
    return address,str(m.get('Subject','Votre demande de transport')),mid


def followup_body(category):
    if category=='mon_exploit':
        return '''Bonjour,

Je reviens une seule fois sur notre présentation de Mon Exploit. Souhaitez-vous étudier un essai pour simplifier les échanges entre le bureau et vos chauffeurs ?
Répondez TEST avec votre nombre de chauffeurs et le point que vous souhaitez améliorer ; nous pouvons avancer par e-mail, sans appel.
Présentation, tarifs et brochure : https://13urgent.fr/mon-exploit.html
L’essai gratuit de 30 jours commence à la remise des accès, après confirmation du périmètre, sans renouvellement payant automatique.

Cordialement,
L’équipe CHRONOSS — Mon Exploit
contact@13urgent.fr
Si vous ne souhaitez plus recevoir nos messages, répondez STOP.
'''
    return '''Bonjour,

Je reviens une seule fois sur notre présentation des services de transport. Avez-vous un envoi ponctuel à organiser pour votre entreprise ?
Vous pouvez nous indiquer départ, arrivée, date, marchandise, poids et volume, sans appel téléphonique.
13 URGENT permet de publier un besoin et d’étudier les propositions reçues : https://13urgent.fr/deposer.html
Pour une étude directe par CHRONOSS : https://13urgent.fr/demander-un-devis.html
Toute offre précise son prix et ses disponibilités avant votre accord. Aucun transport n’est réservé automatiquement.

Cordialement,
L’équipe CHRONOSS — 13 URGENT
contact@13urgent.fr
Si vous ne souhaitez plus recevoir nos messages, répondez STOP.
'''


def execute(path,password,checkpoint,now,deliver=service.deliver,archive_factory=None):
    if not commercial_hours.allowed(now):return {'eligible':0,'followups_accepted':0,'followups_blocked':0,'deferred_business_hours':True}
    path=Path(path);state=json.loads(path.read_text());rows=eligible(state,now)
    if not rows:return {'eligible':0,'followups_accepted':0,'followups_blocked':0}
    archive=archive_factory() if archive_factory else agent.SentArchive(password);accepted=blocked=0
    try:
        for cid,rid,r in rows:
            if not commercial_hours.allowed(now):break
            try:address,subject,mid=original(archive,r)
            except agent.CampaignError:blocked+=1;continue
            category=r.get('service_category','urgent')
            # Download and verify the fixed public PDF before reserving the one attempt.
            attachment=agent.verified_pdf(category)
            payload={'request_id':'direction-relance-'+r['fingerprint'],'to':address,'subject':('Re: '+subject)[:190],'body':followup_body(category)}
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            def build(payload,digest,date):
                mail=service.build_message(payload,digest,date);mail['In-Reply-To']=mid;mail['References']=mid;mail['List-Unsubscribe']='<mailto:'+agent.SENDER+'?subject=STOP>';mail.add_attachment(attachment[0],maintype='application',subtype='pdf',filename=attachment[1]);return mail
            state=json.loads(path.read_text());parent=state['campaigns'][cid][rid];parent.update(followup_count=1,followup_state='intent',followup_attempted_at=now.isoformat());agent.save(path,state);checkpoint()
            result=deliver(payload,digest,path,password,checkpoint,message_builder=build)
            state=json.loads(path.read_text());state['campaigns'][cid][rid]['followup_state']=result['status']
            if result['status']=='deferred_business_hours':state['campaigns'][cid][rid]['followup_count']=0
            agent.save(path,state);checkpoint()
            accepted+=int(result.get('emails_sent',0));blocked+=int(result['status'] not in ('accepted_and_archived','already_recorded','archive_reconciled_without_resend'))
    finally:archive.close()
    return {'eligible':len(rows),'followups_accepted':accepted,'followups_blocked':blocked}


def main():
    password=os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password:raise agent.CampaignError('mail_access_not_connected')
    _,sd=run_campaign.pipeline.setup_runtime();path=sd/'mail-state.json';checkpoint=lambda:run_campaign.checkpoint(sd);now=datetime.now(timezone.utc)
    # Refresh replies and opt-outs immediately before deciding to follow up.
    monitor_replies.monitor(path,password,checkpoint,now=now)
    result=execute(path,password,checkpoint,now);print(json.dumps({'status':'commercial_followup_checked',**result,'delivery_to_recipient_not_verified':True}))
if __name__=='__main__':
    try:main()
    except Exception as e:
        code=str(e) if isinstance(e,agent.CampaignError) and re.fullmatch('[a-z_]+',str(e)) else 'commercial_followup_failed'
        print(json.dumps({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True}));raise SystemExit(2)

"""Read only delivery reports for this campaign; never expose mailbox content."""
from __future__ import annotations
from datetime import datetime,timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
import imaplib,re,ssl
import commercial_agent as agent


def report_failures(raw):
    message=BytesParser(policy=policy.default).parsebytes(raw)
    fingerprints=set();failures=[]
    for part in message.walk():
        mid=str(part.get('Message-ID',''))
        found=re.fullmatch(r'<([0-9a-f]{64})@13urgent\.fr>',mid.strip())
        if found:fingerprints.add(found.group(1))
        if part.get_content_type()=='text/rfc822-headers':
            text=(part.get_payload(decode=True) or b'').decode(errors='replace')
            fingerprints.update(re.findall(r'^Message-ID:\s*<([0-9a-f]{64})@13urgent\.fr>',text,re.M|re.I))
        if part.get_content_type()=='message/delivery-status':
            for block in part.get_payload() if isinstance(part.get_payload(),list) else []:
                if str(block.get('Action','')).lower()!='failed':continue
                code=str(block.get('Status','')).strip()
                if not re.fullmatch(r'5\.\d{1,3}\.\d{1,3}',code):continue
                value=str(block.get('Final-Recipient') or block.get('Original-Recipient') or '')
                address=parseaddr(value.split(';',1)[-1].strip())[1].lower()
                if address:failures.append((address,code))
    return fingerprints,failures


def verify(campaign,state_path,password,checkpoint,imap_factory=None,reported_id=None):
    import json
    from pathlib import Path
    rows=agent.campaign_rows(campaign);state_path=Path(state_path)
    state=json.loads(state_path.read_text())
    records=state.get('campaigns',{}).get(campaign['campaign_id'],{})
    by_id={r['id']:r for r in rows};by_fingerprint={r.get('fingerprint'):rid for rid,r in records.items()}
    changed=False;scanned=0;matched=0
    def mark(rid,code,source):
        nonlocal changed
        record=records.get(rid)
        if not record:raise agent.CampaignError('bounce_record_not_found')
        if record.get('delivery_status')!='hard_bounced' or record.get('delivery_code')!=code:changed=True
        record.update(delivery_status='hard_bounced',delivery_code=code,blocked_for_resend=True,bounce_source=source,bounce_checked_at=datetime.now(timezone.utc).isoformat())
    if reported_id:
        if reported_id not in by_id or not agent.recipient(by_id[reported_id]):raise agent.CampaignError('reported_bounce_outside_campaign')
        mark(reported_id,'5.1.1','owner_delivery_report')
    client=imap_factory() if imap_factory else imaplib.IMAP4_SSL('ssl0.ovh.net',993,ssl_context=ssl.create_default_context(),timeout=30)
    try:
        client.login(agent.SENDER,password)
        status,_=client.select('INBOX',readonly=True)
        if status!='OK':raise agent.CampaignError('delivery_report_folder_not_accessible')
        since=datetime.fromisoformat(campaign['send_not_before'].replace('Z','+00:00')).strftime('%d-%b-%Y')
        status,data=client.search(None,'SINCE',since,'OR','FROM','"MAILER-DAEMON"','FROM','"postmaster"')
        if status!='OK':raise agent.CampaignError('delivery_report_search_failed')
        ids=b' '.join(x for x in data or [] if isinstance(x,bytes)).split()
        for mid in ids[-50:]:
            status,data=client.fetch(mid,'(BODY.PEEK[]<0.262144>)')
            if status!='OK':continue
            raw=b''.join(x[1] for x in data if isinstance(x,tuple) and len(x)>1 and isinstance(x[1],bytes))
            scanned+=1;fingerprints,failures=report_failures(raw)
            for fingerprint in fingerprints:
                rid=by_fingerprint.get(fingerprint)
                if not rid:continue
                row=by_id.get(rid)
                if not row:continue
                for address,code in failures:
                    if address==str(row.get('to','')).lower():mark(rid,code,'matched_delivery_report');matched+=1
    finally:
        try:client.logout()
        except Exception:pass
        # The owner's explicit report is retained even if a later read fails.
        if changed:
            agent.save(state_path,state);checkpoint()
    accepted=sum(r.get('archived_in_sent') is True for r in records.values())
    bounced=sum(r.get('delivery_status')=='hard_bounced' for r in records.values())
    return {'status':'delivery_reports_checked','accepted_and_archived':accepted,'hard_bounced':bounced,'delivery_not_confirmed':max(0,accepted-bounced),'reports_scanned':scanned,'matching_failures':matched,'scan_limited':len(ids)>50,'emails_sent':0}

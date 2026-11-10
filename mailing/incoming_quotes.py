#!/usr/bin/env python3
"""Process quote requests inside the mail executor; never export mailbox content."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import imaplib
import json
import os
from pathlib import Path
import re
import ssl
import time
import unicodedata

import commercial_agent as agent
import run_campaign
import send_service_reply as service

ACTIVATED_AT = datetime.fromisoformat('2026-11-10T13:27:42+00:00')
TASK_FOLDER = 'INBOX.13URGENT-Demandes'
OWN_ID = re.compile(r'<[0-9a-f]{64}@13urgent\.fr>', re.I)
MESSAGE_ID = re.compile(r'<[^<>\s\r\n]{1,200}>')
EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TARGET_SIGNATURE_HASH = 'e738b5c88eab92723cb19a47894bbf33287c834ac7a092264548f181a09c3753'


def folded(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c)).casefold().split())


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(); self.values = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
        if tag in ('br', 'p', 'div', 'tr'): self.values.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.values.append(data)


def body_text(message):
    plain, html = [], []
    attachments = False
    for part in message.walk():
        if part.get_content_disposition() == 'attachment' or (part.get_filename() and part.get_content_disposition() != 'inline'):
            attachments = True; continue
        if part.get_content_type() not in ('text/plain', 'text/html'): continue
        try: value = part.get_content()
        except (LookupError, UnicodeError, ValueError): continue
        if not isinstance(value, str): continue
        if part.get_content_type() == 'text/plain': plain.append(value)
        else: html.append(value)
    if plain: return '\n'.join(plain)[:40000], attachments
    parser = PlainHTML(); parser.feed('\n'.join(html)[:100000])
    return ''.join(parser.values)[:40000], attachments


def current_text(text):
    kept = []
    for line in text.splitlines():
        if (re.match(r'^\s*>', line) or re.match(r'^\s*(?:From|De)\s*:', line, re.I)
                or re.match(r'^\s*(?:On .+ wrote:|Le .+ [ée]crit\s*:)', line, re.I)
                or re.match(r'^\s*[-_]{5,}', line)):
            break
        kept.append(line)
    return '\n'.join(kept)


def single_address(header):
    if not header or '\r' in str(header) or '\n' in str(header): return None
    addresses = getaddresses([str(header)])
    if len(addresses) != 1: return None
    address = addresses[0][1]
    return address if EMAIL.fullmatch(address) and len(address) <= 254 else None


def describe(raw, received_at=None):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    sender = single_address(message.get('From'))
    if not sender or sender.lower() in (agent.SENDER, agent.COPY): return None
    local = sender.lower().split('@')[0]
    if (local in ('mailer-daemon', 'postmaster', 'noreply', 'no-reply')
            or message.get_content_type() == 'multipart/report'
            or str(message.get('Auto-Submitted', 'no')).lower().strip() != 'no'
            or str(message.get('Precedence', '')).lower().strip() in ('bulk', 'list', 'junk')
            or message.get('List-Id') or message.get('List-Unsubscribe')
            or message.get('X-Autoreply') or message.get('X-Autorespond')
            or str(message.get('X-Spam-Flag', '')).upper() == 'YES'
            or '[spam]' in str(message.get('Subject', '')).lower()): return None
    reply_to = single_address(message.get('Reply-To')) if message.get('Reply-To') else sender
    if not reply_to or reply_to.lower().split('@')[-1] != sender.lower().split('@')[-1]: return None
    if reply_to.lower() in (agent.SENDER, agent.COPY): return None
    mid = str(message.get('Message-ID', '')).strip()
    if not MESSAGE_ID.fullmatch(mid): return None
    text, attachments = body_text(message); text = current_text(text)
    first = next((line.strip() for line in text.splitlines() if line.strip()), '')
    if re.fullmatch(r'STOP[.!]?', first, re.I): return None
    references = MESSAGE_ID.findall(str(message.get('References', '')) + ' ' + str(message.get('In-Reply-To', '')))
    follows_own = bool(OWN_ID.search(' '.join(references)))
    if received_at is None:
        try: received_at = parsedate_to_datetime(str(message.get('Date', '')))
        except (ValueError, TypeError): received_at = None
    if received_at is None or received_at.utcoffset() is None: return None
    normalized = folded(text)
    kind = 'linked_followup' if follows_own else None
    signature_hash = TARGET_SIGNATURE_HASH
    sender_label = getaddresses([str(message.get('From', ''))])[0][0]
    signature_words = re.findall(r'[a-z]+', folded('\n'.join(text.splitlines()[-16:]) + ' ' + sender_label))
    signature_found = any(hashlib.sha256(word.encode()).hexdigest() == signature_hash for word in signature_words)
    if signature_found:
        if 'tandoori' in normalized and 'palette' in normalized: kind = 'pallets_uk'
        if 'refroidisseur' in normalized and ('be-200' in normalized or 'bouteille' in normalized): kind = 'equipment_be_fr'
    request = bool(re.search(r'(?:offre|devis|demande|besoin).{0,45}(?:transport|livraison|enlevement)|(?:transport|livraison).{0,45}(?:offre|devis|demande)', normalized))
    facts = sum(bool(re.search(pattern, normalized)) for pattern in
                (r'\b\d+(?:[.,]\d+)?\s*kg\b', r'\bpalettes?\b', r'\b(?:adresse|address|pick.up)\b', r'\b\d{4,5}\b', r'\b(?:dimensions?|mm|cm)\b'))
    if not kind and request and facts >= 2: kind = 'generic_quote'
    if not kind: return None
    clean_subject = ' '.join(str(message.get('Subject', 'Demande de transport')).split())[:180]
    source_hash = hashlib.sha256(mid.encode()).hexdigest()
    return {'kind': kind, 'sender': sender, 'recipient': reply_to, 'message_id': mid,
            'references': list(dict.fromkeys(references))[-18:], 'subject': clean_subject,
            'text': text, 'attachments': attachments, 'follows_own': follows_own,
            'source_hash': source_hash, 'received_at': received_at.astimezone(timezone.utc)}


def select_requests(messages, mode, now=None):
    now = now or datetime.now(timezone.utc)
    rows = [x for x in (describe(raw, received) for raw, received in messages) if x]
    if mode in ('probe_requests', 'reply_requests'):
        selected = []
        for kind in ('pallets_uk', 'equipment_be_fr'):
            candidates = [x for x in rows if x['kind'] == kind and not x['follows_own']]
            if candidates: selected.append(max(candidates, key=lambda x: x['received_at']))
        return selected
    return sorted((x for x in rows if x['received_at'] >= max(ACTIVATED_AT, now - timedelta(days=2))),
                  key=lambda x: x['received_at'])[:30]


def missing_fields(request):
    t = folded(request['text'])
    fields = []
    if not re.search(r'\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}(?:[-/]20\d{2})?)\b', t): fields.append('dates')
    if not re.search(r'\b\d+(?:[.,]\d+)?\s*kg\b', t): fields.append('weight')
    if not re.search(r'\b(?:palettes?|dimensions?|mm|cm)\b', t): fields.append('packaging')
    if not any(word in t for word in ('adresse', 'address', 'depart', 'destination', 'enlevement')): fields.append('addresses')
    return fields


def reply_body(request):
    if request['kind'] == 'pallets_uk':
        return """Bonjour,

Merci pour votre demande de transport palettisé.

Pour préparer notre offre, pouvez-vous préciser :
- les dates souhaitées d’enlèvement et de livraison et les plages horaires d’accès ;
- les moyens de chargement et de déchargement disponibles et si un hayon est nécessaire ;
- qui prend en charge les formalités douanières d’exportation au Royaume-Uni et d’importation en France ?

Cordialement,
L’équipe CHRONOSS — 13 URGENT
contact@13urgent.fr"""
    if request['kind'] == 'equipment_be_fr':
        return """Bonjour,

Merci pour votre demande de transport de matériel.

Pour préparer notre offre, pouvez-vous préciser :
- les dates souhaitées d’enlèvement et de livraison et les plages horaires d’accès ;
- si l’appareil sera emballé et palettisé, avec les dimensions finales du conditionnement ;
- les moyens de chargement et de déchargement disponibles et si un hayon est nécessaire ?

Cordialement,
L’équipe CHRONOSS — 13 URGENT
contact@13urgent.fr"""
    questions = {'dates': 'les dates souhaitées d’enlèvement et de livraison et les plages horaires',
                 'weight': 'le poids total de la marchandise', 'packaging': 'le conditionnement, le nombre de palettes et les dimensions',
                 'addresses': 'les villes et codes postaux d’enlèvement et de livraison'}
    missing = missing_fields(request)
    detail = ('Pour préparer notre offre, pouvez-vous préciser :\n' + '\n'.join('- ' + questions[x] + ' ;' for x in missing)
              + '\nMerci également d’indiquer les moyens de chargement et de déchargement disponibles.') if missing else (
              'Votre demande a bien été reçue pour étude et chiffrage. Ce message est un accusé de réception ; il ne confirme ni un tarif, ni une réservation de transport.')
    return 'Bonjour,\n\nMerci pour votre demande de transport.\n\n' + detail + '\n\nCordialement,\nL’équipe CHRONOSS — 13 URGENT\ncontact@13urgent.fr'


def payload_for(request):
    subject = request['subject']
    if not re.match(r'^re\s*:', subject, re.I): subject = 'Re: ' + subject
    return {'request_id': 'inbound-' + request['source_hash'], 'to': request['recipient'],
            'subject': subject, 'body': reply_body(request)}


def message_builder(request):
    def build(payload, digest, date):
        mail = service.build_message(payload, digest, date)
        mail['In-Reply-To'] = request['message_id']
        mail['References'] = ' '.join(list(dict.fromkeys(request['references'] + [request['message_id']])))
        mail['Auto-Submitted'] = 'auto-replied'
        return mail
    return build


def read_messages(client, mode, now):
    status, _ = client.select('INBOX', readonly=True)
    if status != 'OK': raise agent.CampaignError('incoming_inbox_not_accessible')
    since = '01-Oct-2026' if mode in ('probe_requests', 'reply_requests') else (now - timedelta(days=2)).strftime('%d-%b-%Y')
    status, data = client.uid('SEARCH', None, 'SINCE', since)
    if status != 'OK': raise agent.CampaignError('incoming_search_failed')
    ids = b' '.join(x for x in data or [] if isinstance(x, bytes)).split()
    messages = []
    for uid in ids[-300:]:
        status, data = client.uid('FETCH', uid, '(INTERNALDATE BODY.PEEK[]<0.262144>)')
        if status != 'OK': continue
        for part in data or []:
            if not isinstance(part, tuple) or not isinstance(part[1], bytes): continue
            received = None
            match = re.search(rb'INTERNALDATE "([^"]+)"', part[0])
            if match:
                try: received = datetime.strptime(match.group(1).decode('ascii'), '%d-%b-%Y %H:%M:%S %z')
                except ValueError: pass
            if len(part[1]) < 262144: messages.append((part[1], received))
    return messages, len(ids) > 300


def private_task(client, request, status):
    folder = '"' + TASK_FOLDER + '"'
    selected, _ = client.select(folder)
    if selected != 'OK':
        client.create(folder)
        selected, _ = client.select(folder)
    if selected != 'OK': return False
    client.subscribe(folder)
    task_id = request['source_hash'] + '-' + status
    code, rows = client.uid('SEARCH', None, 'HEADER', 'X-13URGENT-Task-ID', '"' + task_id + '"')
    if code != 'OK': return False
    if any(x.strip() for x in rows or [] if isinstance(x, bytes)): return True
    task = EmailMessage(policy=policy.SMTP)
    task['From'] = agent.SENDER; task['To'] = agent.SENDER
    task['Subject'] = '[13URGENT — ' + status + '] ' + request['subject']
    task['X-13URGENT-Task-ID'] = task_id
    task.set_content('État : ' + status + '\nCorrespondant : ' + request['sender'] + '\nReçu le : '
                     + request['received_at'].isoformat() + '\n\nDemande reçue :\n' + request['text'])
    result, _ = client.append(folder, None, imaplib.Time2Internaldate(time.time()), task.as_bytes())
    return result == 'OK'


def note(state_path, request, status, checkpoint, task_saved=False):
    state_path = Path(state_path)
    state = json.loads(state_path.read_text()) if state_path.exists() else {'schema_version': 1, 'campaigns': {}, 'suppressed': []}
    record = state['campaigns'].setdefault('inbound-requests-v1', {}).setdefault(request['source_hash'], {})
    record.update(inquiry_kind=request['kind'], workflow_status=status, received_at=request['received_at'].isoformat(),
                  task_archive_saved=task_saved, checked_at=datetime.now(timezone.utc).isoformat())
    agent.save(state_path, state); checkpoint()


def process(requests, state_path, password, checkpoint, client, deliver=service.deliver):
    counts = {}; sent = copies = task_failures = 0; domains = {}
    for request in requests:
        domain = request['recipient'].lower().split('@')[-1]
        if sent >= 10 or domains.get(domain, 0) >= 2: status = 'rate_limit_held'
        elif request['attachments'] and request['kind'] not in ('pallets_uk', 'equipment_be_fr'): status = 'attachments_need_review'
        elif request['follows_own']: status = 'followup_needs_review'
        else:
            payload = payload_for(request)
            digest = hashlib.sha256(json.dumps({'payload': payload, 'parent': request['message_id']}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            note(state_path, request, 'reply_prepared', checkpoint)
            result = deliver(payload, digest, state_path, password, checkpoint, message_builder=message_builder(request))
            status = result['status']; sent += result.get('emails_sent', 0)
            copies += int(result.get('copy_saved_in_sent') is True)
            domains[domain] = domains.get(domain, 0) + result.get('emails_sent', 0)
        task_status = ('A_COMPLETER' if request['kind'] in ('pallets_uk', 'equipment_be_fr') or missing_fields(request) else 'A_CHIFFRER')
        if status in ('attachments_need_review', 'followup_needs_review'): task_status = 'A_VERIFIER'
        try: saved = private_task(client, request, task_status)
        except Exception: saved = False
        if not saved: task_failures += 1
        note(state_path, request, status, checkpoint, saved)
        counts[status] = counts.get(status, 0) + 1
    return {'status': 'incoming_requests_processed', 'counts': counts, 'emails_sent': sent,
            'copies_saved_in_sent': copies, 'private_task_archive_failures': task_failures,
            'delivery_to_recipient_not_verified': True, 'price_or_booking_confirmed': False,
            'publications_created': 0}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--mode', choices=['probe_requests', 'reply_requests', 'automatic'], default='probe_requests')
    args = parser.parse_args(); password = os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password: raise agent.CampaignError('mail_access_not_connected')
    now = datetime.now(timezone.utc)
    client = imaplib.IMAP4_SSL('ssl0.ovh.net', 993, ssl_context=ssl.create_default_context(), timeout=30)
    try:
        client.login(agent.SENDER, password)
        messages, limited = read_messages(client, args.mode, now)
        requests = select_requests(messages, args.mode, now)
        if args.mode == 'probe_requests':
            print(json.dumps({'status': 'incoming_quote_probe', 'requests_found': len(requests),
                              'types': [r['kind'] for r in requests],
                              'received_dates': [r['received_at'].date().isoformat() for r in requests],
                              'attachments_held': sum(r['attachments'] for r in requests),
                              'scan_limited': limited, 'emails_sent': 0})); return 0
        _, state_dir = run_campaign.pipeline.setup_runtime()
        result = process(requests, state_dir / 'mail-state.json', password,
                         lambda: run_campaign.checkpoint(state_dir), client)
        result['scan_limited'] = limited
        print(json.dumps(result))
        return 0 if not any(key in result['counts'] for key in ('uncertain_do_not_retry', 'accepted_archive_pending', 'partial_acceptance', 'blocked_previous_uncertain_result')) else 2
    finally:
        try: client.logout()
        except Exception: pass


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as error:
        code = str(error) if isinstance(error, agent.CampaignError) and re.fullmatch('[a-z0-9_]+', str(error)) else 'incoming_quote_worker_failed'
        print(json.dumps({'status': 'blocked', 'error': code, 'emails_sent_in_this_step_not_confirmed': True})); raise SystemExit(2)

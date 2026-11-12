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


def describe(raw, received_at=None, allow_followup=False):
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
    if not kind and allow_followup and text.strip(): kind = 'unclassified_followup'
    if not kind: return None
    clean_subject = ' '.join(str(message.get('Subject', 'Demande de transport')).split())[:180]
    source_hash = hashlib.sha256(mid.encode()).hexdigest()
    return {'kind': kind, 'sender': sender, 'recipient': reply_to, 'message_id': mid,
            'references': list(dict.fromkeys(references))[-18:], 'subject': clean_subject,
            'text': text, 'attachments': attachments, 'follows_own': follows_own,
            'source_hash': source_hash, 'received_at': received_at.astimezone(timezone.utc),
            'source_truncated': len(raw) >= 262144}


def parent_inquiry(request, state):
    """Resolve a source inquiry through known message hashes, never subject guessing."""
    campaigns = state.get('campaigns', {})
    inquiries = campaigns.get('inbound-requests-v1', {})
    outgoing = campaigns.get('service-replies-v1', {})
    fingerprints = {r.get('fingerprint'): key[len('inbound-'):]
                    for key, r in outgoing.items() if key.startswith('inbound-')}
    parents = set()
    for reference in request['references']:
        source_hash = hashlib.sha256(reference.encode()).hexdigest()
        if source_hash in inquiries: parents.add(source_hash)
        if OWN_ID.fullmatch(reference):
            known = fingerprints.get(reference[1:].split('@', 1)[0].lower())
            if known in inquiries: parents.add(known)
    if len(parents) != 1: return None
    record = inquiries[next(iter(parents))]
    kind = record.get('inquiry_kind')
    return kind if kind in ('pallets_uk', 'equipment_be_fr') else None


def select_followup(messages, state, sender_hash, audit=None):
    if not re.fullmatch(r'[0-9a-f]{64}', sender_hash or ''):
        raise agent.CampaignError('followup_sender_hash_invalid')
    selected = []
    counts = {'target_sender_messages_seen': 0, 'target_ready_candidates_seen': 0,
              'linked_candidates_seen': 0}
    for raw, received in messages:
        header = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
        sender = single_address(header.get('From'))
        if not sender or hashlib.sha256(sender.lower().encode()).hexdigest() != sender_hash:
            continue
        counts['target_sender_messages_seen'] += 1
        request = describe(raw, received, allow_followup=True)
        if not request: continue
        kind = parent_inquiry(request, state)
        if kind: counts['linked_candidates_seen'] += 1
        text = folded(request['text'])
        ready = bool(re.search(r'\b(?:pret|prete|prets|pretes|immediat|immediate)\b', text)
                     and any(word in text for word in ('hayon', 'chariot')))
        if ready: counts['target_ready_candidates_seen'] += 1
        if kind and ready:
            selected.append({**request, 'parent_kind': kind})
    if audit is not None: audit.update(counts)
    return [max(selected, key=lambda r: r['received_at'])] if selected else []


def followup_body(request, now=None):
    now = now or datetime.now(timezone.utc)
    delayed = now - request['received_at'] > timedelta(days=1)
    questions = [
        '- les horaires exacts d’ouverture aux deux adresses ;',
        '- si un chariot élévateur ou un autre moyen de chargement est disponible à l’enlèvement ;',
    ]
    if request['parent_kind'] == 'equipment_be_fr':
        questions.append('- le nombre de colis ou palettes prêts et les dimensions finales du conditionnement.')
    else:
        questions.append('- qui prend en charge les formalités douanières d’exportation et d’importation.')
    if delayed:
        questions.insert(0, '- si le colis est toujours disponible à l’enlèvement ;')
    introduction = 'Merci pour votre retour et la photo.'
    if delayed:
        introduction += ' Veuillez nous excuser pour le délai de réponse.'
    return ('Bonjour,\n\n' + introduction + ' Vous nous avez indiqué que le colis était prêt '
            'pour un enlèvement dès que possible pendant les horaires de travail. Le besoin d’un hayon ou d’un chariot '
            'au déchargement est bien pris en compte.\n\nPour finaliser notre étude, pouvez-vous préciser :\n'
            + '\n'.join(questions)
            + '\n\nCordialement,\nL’équipe CHRONOSS — 13 URGENT\ncontact@13urgent.fr')


def process_followup(requests, state_path, password, checkpoint, client, deliver=service.deliver):
    if not requests:
        return {'status': 'followup_not_matched', 'emails_sent': 0, 'copies_saved_in_sent': 0}
    request = requests[0]
    payload = payload_for(request)
    payload['request_id'] = 'followup-' + request['source_hash']
    state = json.loads(Path(state_path).read_text())
    previous = state.get('campaigns', {}).get('service-replies-v1', {}).get(payload['request_id'])
    if previous and previous.get('status') == 'accepted_and_archived':
        return {'status': 'already_recorded', 'emails_sent': 0, 'copy_saved_in_sent': True,
                'parent_kind': request['parent_kind'], 'price_or_booking_confirmed': False,
                'publications_created': 0}
    reply_time = parsedate_to_datetime(previous['message_date']) if previous and previous.get('message_date') else None
    payload['body'] = followup_body(request, now=reply_time)
    digest = hashlib.sha256(json.dumps({'payload': payload, 'parent': request['message_id']},
                                      ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    result = deliver(payload, digest, state_path, password, checkpoint,
                     message_builder=message_builder(request))
    try: saved = private_task(client, request, 'EN_ATTENTE_PRECISIONS')
    except Exception: saved = False
    note(state_path, request, result['status'], checkpoint, saved)
    return {**result, 'parent_kind': request['parent_kind'], 'private_task_archive_saved': saved,
            'price_or_booking_confirmed': False, 'publications_created': 0}


def select_requests(messages, mode, now=None):
    now = now or datetime.now(timezone.utc)
    rows = [x for x in (describe(raw, received) for raw, received in messages) if x]
    if mode in ('probe_requests', 'reply_requests'):
        selected = []
        for kind in ('pallets_uk', 'equipment_be_fr'):
            candidates = [x for x in rows if x['kind'] == kind]
            if candidates:
                chosen = max(candidates, key=lambda x: x['received_at'])
                selected.append({**chosen, 'explicitly_requested_reply': mode == 'reply_requests'})
        return selected
    return sorted((x for x in rows if x['received_at'] >= max(ACTIVATED_AT, now - timedelta(days=2))),
                  key=lambda x: x['received_at'])


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
    since = '01-Oct-2026' if mode in ('probe_requests', 'reply_requests', 'probe_followup', 'reply_followup') else (now - timedelta(days=2)).strftime('%d-%b-%Y')
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
            # Keep the readable text/header prefix of photo-heavy messages for
            # private triage. Attachments are neither opened nor fetched fully.
            messages.append((part[1], received))
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


def unprocessed_requests(requests, state_path):
    state_path = Path(state_path)
    state = json.loads(state_path.read_text()) if state_path.exists() else {'campaigns': {}}
    records = state.get('campaigns', {}).get('inbound-requests-v1', {})
    terminal = {'accepted_and_archived', 'already_recorded', 'archive_reconciled_without_resend',
                'attachments_need_review', 'followup_needs_review', 'uncertain_do_not_retry',
                'blocked_previous_uncertain_result', 'blocked_previous_intent', 'partial_acceptance',
                'content_conflict', 'partial_message_needs_review'}
    pending, skipped = [], 0
    for request in requests:
        record = records.get(request['source_hash'], {})
        if record.get('task_archive_saved') is True and record.get('workflow_status') in terminal:
            skipped += 1
        else:
            # Accepted-but-not-archived deliveries and failed private task copies
            # remain eligible for their existing repair paths; never resend them.
            pending.append(request)
    return pending[:30], skipped


def process(requests, state_path, password, checkpoint, client, deliver=service.deliver, automatic=False):
    skipped = 0
    if automatic: requests, skipped = unprocessed_requests(requests, state_path)
    counts = {}; sent = copies = task_failures = 0; domains = {}
    for request in requests:
        domain = request['recipient'].lower().split('@')[-1]
        if sent >= 10 or domains.get(domain, 0) >= 2: status = 'rate_limit_held'
        elif request.get('source_truncated') and not request.get('explicitly_requested_reply', False): status = 'partial_message_needs_review'
        elif request['attachments'] and request['kind'] not in ('pallets_uk', 'equipment_be_fr'): status = 'attachments_need_review'
        elif request['follows_own'] and not request.get('explicitly_requested_reply', False): status = 'followup_needs_review'
        else:
            payload = payload_for(request)
            digest = hashlib.sha256(json.dumps({'payload': payload, 'parent': request['message_id']}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            note(state_path, request, 'reply_prepared', checkpoint)
            result = deliver(payload, digest, state_path, password, checkpoint, message_builder=message_builder(request))
            status = result['status']; sent += result.get('emails_sent', 0)
            copies += int(result.get('copy_saved_in_sent') is True)
            domains[domain] = domains.get(domain, 0) + result.get('emails_sent', 0)
        task_status = ('A_COMPLETER' if request['kind'] in ('pallets_uk', 'equipment_be_fr') or missing_fields(request) else 'A_CHIFFRER')
        if status in ('attachments_need_review', 'followup_needs_review', 'partial_message_needs_review'): task_status = 'A_VERIFIER'
        try: saved = private_task(client, request, task_status)
        except Exception: saved = False
        if not saved: task_failures += 1
        note(state_path, request, status, checkpoint, saved)
        counts[status] = counts.get(status, 0) + 1
    return {'status': 'incoming_requests_processed', 'counts': counts, 'emails_sent': sent,
            'copies_saved_in_sent': copies, 'private_task_archive_failures': task_failures,
            'already_processed_skipped': skipped,
            'delivery_to_recipient_not_verified': True, 'price_or_booking_confirmed': False,
            'publications_created': 0}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--mode', choices=['probe_requests', 'reply_requests', 'probe_followup', 'reply_followup', 'automatic'], default='probe_requests')
    args = parser.parse_args(); password = os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password: raise agent.CampaignError('mail_access_not_connected')
    now = datetime.now(timezone.utc)
    client = imaplib.IMAP4_SSL('ssl0.ovh.net', 993, ssl_context=ssl.create_default_context(), timeout=30)
    try:
        client.login(agent.SENDER, password)
        messages, limited = read_messages(client, args.mode, now)
        if args.mode in ('probe_followup', 'reply_followup'):
            _, state_dir = run_campaign.pipeline.setup_runtime()
            state_path = state_dir / 'mail-state.json'
            audit = {}
            requests = select_followup(messages, json.loads(state_path.read_text()),
                                       os.environ.get('TARGET_SENDER_SHA256', ''), audit=audit)
            if args.mode == 'probe_followup':
                print(json.dumps({'status': 'followup_probe', 'requests_found': len(requests),
                    'parent_kinds': [r['parent_kind'] for r in requests],
                    'received_dates': [r['received_at'].date().isoformat() for r in requests],
                    'source_truncated': [r['source_truncated'] for r in requests],
                    'attachments_present': [r['attachments'] for r in requests],
                    'scan_limited': limited, 'emails_sent': 0, **audit})); return 0
            result = process_followup(requests, state_path, password,
                lambda: run_campaign.checkpoint(state_dir), client)
            result['scan_limited'] = limited
            print(json.dumps(result))
            return 0 if result['status'] in ('accepted_and_archived', 'already_recorded', 'archive_reconciled_without_resend', 'followup_not_matched') else 2
        requests = select_requests(messages, args.mode, now)
        if args.mode == 'probe_requests':
            print(json.dumps({'status': 'incoming_quote_probe', 'requests_found': len(requests),
                              'types': [r['kind'] for r in requests],
                              'received_dates': [r['received_at'].date().isoformat() for r in requests],
                              'attachments_held': sum(r['attachments'] for r in requests),
                              'scan_limited': limited, 'emails_sent': 0})); return 0
        _, state_dir = run_campaign.pipeline.setup_runtime()
        result = process(requests, state_dir / 'mail-state.json', password,
                         lambda: run_campaign.checkpoint(state_dir), client, automatic=args.mode == 'automatic')
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

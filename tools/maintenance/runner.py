#!/usr/bin/env python3
"""Use an owner-authorized Actions secret with a pinned server identity."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'mailing'))
import send_service_reply as sealed


def ssh(application, operation, payload=None):
    if application not in ('ecmr','tms') or operation not in ('status','diagnose','deploy'):
        raise ValueError('invalid_operation')
    key = os.environ.get('CHRONOSS_MAINTENANCE_SSH_KEY','').replace('\r\n','\n').lstrip('\ufeff').strip()
    if not key.startswith('-----BEGIN OPENSSH PRIVATE KEY-----'):
        raise ValueError('maintenance_secret_missing')
    with tempfile.TemporaryDirectory(prefix='chronoss-ssh-') as temporary:
        private=Path(temporary)/'key'
        private.write_text(key+'\n');private.chmod(0o600)
        command=operation+' '+application
        raw=None
        if operation=='deploy':
            if not isinstance(payload,dict) or set(payload)!={'application','archive_sha256','archive_base64'} or payload['application']!=application:
                raise ValueError('deployment_fields_invalid')
            digest=payload['archive_sha256']
            raw=base64.b64decode(payload['archive_base64'],validate=True)
            if not re.fullmatch('[0-9a-f]{64}',digest) or not raw or len(raw)>5_000_000 or hashlib.sha256(raw).hexdigest()!=digest:
                raise ValueError('deployment_archive_invalid')
            command+=' '+digest
        result=subprocess.run(['ssh','-T','-i',str(private),'-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','-o','UserKnownHostsFile='+str(REPO/'tools/maintenance/known_hosts'),'root@31.70.119.118',command],input=raw,capture_output=True,timeout=1500)
        if result.returncode:
            raise ValueError('remote_operation_failed')
        return json.loads(result.stdout)


def main():
    mode=sys.argv[1]
    if mode=='prepare':
        _,_,directory=sealed.settings();sealed.prepare(directory)
        print(json.dumps({'status':'maintenance_public_certificate_ready'}));return
    operation=os.environ.get('MAINTENANCE_OPERATION','status')
    application=os.environ.get('MAINTENANCE_APPLICATION','ecmr')
    payload=None
    if operation=='deploy':
        request,digest,directory=sealed.settings()
        try:
            raw=sealed.fetch_payload(request,directory,max_sealed_bytes=7_000_000)
            if len(raw)>6_800_000 or hashlib.sha256(raw).hexdigest()!=digest:
                raise ValueError('deployment_request_digest_invalid')
            payload=json.loads(raw)
        finally:
            for name in ('private.key','request.cms'):(directory/name).unlink(missing_ok=True)
    result=ssh(application,operation,payload)
    report=Path(os.environ['RUNNER_TEMP'])/'maintenance-result.json'
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'application':application,'operation':operation,'status':result.get('status','diagnostic_complete'),'result_saved':True}))


if __name__=='__main__':
    try:main()
    except Exception as e:
        code=str(e) if isinstance(e,ValueError) and re.fullmatch('[a-z_]+',str(e)) else 'maintenance_runner_failed'
        print(json.dumps({'status':'failed','error':code}));sys.exit(1)

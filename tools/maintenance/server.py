#!/usr/bin/env python3
"""Restricted maintenance entry point for the two existing CHRONOSS services.

Only this public SSH key and generic deployment code are installed. No passwords,
application databases, or application source are embedded in this file.
"""
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import zipfile

PUBLIC_KEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGRzy5phJgdwFD7ztkxUU2GavY+09K9r1jxtp5Msr18l chronoss-maintenance-20261120'
INSTALLED = Path('/usr/local/sbin/chronoss-maintenance.py')
ROOTS = {'ecmr': Path('/opt/chronoss-ecmr'), 'tms': Path('/opt/13urgent-tms')}
MAX_ZIP = 5_000_000
MAX_EXPANDED = 20_000_000


def command_parts(value):
    parts = shlex.split(value)
    if len(parts) == 2 and parts[0] in ('status', 'diagnose') and parts[1] in ROOTS:
        return parts
    if len(parts) == 3 and parts[0] == 'deploy' and parts[1] in ROOTS and re.fullmatch('[0-9a-f]{64}', parts[2]):
        return parts
    raise ValueError('command_not_allowed')


def allowed_path(app, name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or str(p) != name:
        return False
    if any(piece.startswith('.') and piece != '.dockerignore' for piece in p.parts):
        return False
    if any(piece in ('__pycache__', 'data', 'private-data', 'backups', 'node_modules') for piece in p.parts):
        return False
    if p.suffix in ('.sqlite', '.sqlite3', '.key', '.pem', '.env') or 'test-access' in name:
        return False
    if app == 'ecmr':
        return (len(p.parts) == 1 and (p.suffix == '.py' or name in ('Dockerfile', '.dockerignore', 'requirements.txt'))
                or p.parts[0] in ('static', 'fonts') and p.suffix.lower() in ('.html', '.js', '.css', '.png', '.jpg', '.svg', '.webmanifest', '.ttf', '.txt')
                or name in ('deploy/update_v11.py', 'deploy/maj-v11-empreintes.json', 'deploy/mail_diagnostics.py'))
    return (name in ('Dockerfile.pilot', '.dockerignore', 'requirements.txt', 'pilot_server.py', 'deploy/backup.py')
            or p.parts[0] in ('prototype', 'examples') and p.suffix.lower() in ('.py', '.js', '.css', '.html', '.json', '.png', '.svg', '.txt', '.ttf', '.csv'))


def unpack(raw, app, digest):
    if not raw or len(raw) > MAX_ZIP or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('archive_digest_or_size_invalid')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        info = z.infolist()
        names = [i.filename for i in info]
        if len(info) > 200 or len(names) != len(set(names)) or sum(i.file_size for i in info) > MAX_EXPANDED:
            raise ValueError('archive_limits_invalid')
        for i in info:
            if i.is_dir() or stat.S_ISLNK(i.external_attr >> 16) or i.flag_bits & 1:
                raise ValueError('archive_entry_invalid')
            if i.filename != 'maintenance-manifest.json' and not allowed_path(app, i.filename):
                raise ValueError('archive_path_not_allowed')
        manifest = json.loads(z.read('maintenance-manifest.json'))
        if not isinstance(manifest, dict) or manifest.get('application') != app or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', str(manifest.get('version', ''))):
            raise ValueError('manifest_invalid')
        hashes = manifest.get('files')
        if not isinstance(hashes, dict) or set(hashes) != set(names) - {'maintenance-manifest.json'} or not hashes:
            raise ValueError('manifest_files_invalid')
        files = {name: z.read(name) for name in hashes}
        if any(hashlib.sha256(data).hexdigest() != hashes[name] for name, data in files.items()):
            raise ValueError('file_digest_invalid')
        required = {'app.py', 'server.py', 'deploy/update_v11.py', 'deploy/maj-v11-empreintes.json', 'Dockerfile'} if app == 'ecmr' else {'pilot_server.py', 'Dockerfile.pilot'}
        if not required <= set(files):
            raise ValueError('archive_runtime_incomplete')
        if app == 'ecmr':
            transferred = json.loads(files['deploy/maj-v11-empreintes.json']).get('files', {})
            if not transferred or any(name not in files or hashlib.sha256(files[name]).hexdigest() != digest for name, digest in transferred.items()):
                raise ValueError('application_manifest_invalid')
        return manifest, files


def compose(app):
    root = ROOTS[app]
    return ['docker', 'compose'] if app == 'ecmr' else ['docker', 'compose', '--env-file', str(root/'deploy/pilot.env'), '-f', str(root/'deploy/compose.pilot.yaml')]


def run(args, app, **kwargs):
    return subprocess.run(args, cwd=ROOTS[app], env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/bin', 'HOME': '/root', 'LANG': 'C.UTF-8'}, check=True, capture_output=True, timeout=900, **kwargs)


def status(app):
    result = {'application': app, 'read_only': True, 'application_changes': 0, 'emails_submitted': 0, 'services': {}}
    if not ROOTS[app].is_dir():
        return {**result, 'status': 'directory_missing'}
    for service in (('app', 'worker', 'https') if app == 'ecmr' else ('tms',)):
        try:
            cid = run(compose(app)+['ps', '-q', service], app).stdout.decode().strip()
            if not re.fullmatch('[a-f0-9]{12,64}', cid):
                result['services'][service] = {'state': 'not_running'}
                continue
            info = json.loads(run(['docker', 'inspect', '--format', '{{json .State}}', cid], app).stdout)
            result['services'][service] = {'state': info['Status'], 'health': info.get('Health', {}).get('Status', 'not_configured')}
        except Exception:
            result['services'][service] = {'state': 'inspection_failed'}
    result['status'] = 'inspection_complete'
    return result


def diagnose(app):
    if app == 'ecmr':
        source = ROOTS[app]/'deploy/mail_diagnostics.py'
        if source.is_file():
            value = json.loads(run(['/usr/bin/python3', str(source)], app).stdout)
            return {'application': app, 'diagnostic': value}
    return status(app)


def deploy(app, digest, raw):
    manifest, files = unpack(raw, app, digest)
    root = ROOTS[app]
    if not root.is_dir():
        raise ValueError('application_directory_missing')
    base = root/'.maintenance'
    base.mkdir(mode=0o700, exist_ok=True)
    with (base/'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = base/('applied-'+digest+'.json')
        if receipt.exists():
            return {**json.loads(receipt.read_text()), 'already_applied': True}
        for name in files:
            destination = root/name
            if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents if parent != root.parent):
                raise ValueError('destination_symlink_not_allowed')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = base/('source-'+stamp)
        backup.mkdir(mode=0o700)
        previous = {}
        for name in files:
            p = root/name
            previous[name] = p.is_file()
            if p.is_file():
                target = backup/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
        image = None
        if app == 'tms':
            cid = run(compose(app)+['ps','-q','tms'], app).stdout.decode().strip()
            image = run(['docker','inspect','--format','{{.Image}}',cid], app).stdout.decode().strip()
            run(['docker','image','tag',image,'13urgent-tms:before-maintenance-'+stamp.lower()], app)
            run(['/usr/bin/python3',str(root/'deploy/backup_host.py')], app)
        try:
            for name, data in files.items():
                target = root/name
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
                    tmp.write(data)
                os.chmod(tmp.name, 0o644)
                os.replace(tmp.name, target)
            if app == 'ecmr':
                run(['/usr/bin/python3',str(root/'deploy/update_v11.py')], app)
            else:
                run(compose(app)+['build','tms'], app)
                run(compose(app)+['up','-d','--no-build','--wait','--wait-timeout','120','tms'], app)
        except Exception:
            for name, existed in previous.items():
                if existed: shutil.copy2(backup/name, root/name)
                else: (root/name).unlink(missing_ok=True)
            if image:
                run(['docker','image','tag',image,'13urgent-tms:pilot'], app)
                run(compose(app)+['up','-d','--no-build','--wait','--wait-timeout','120','tms'], app)
            raise
        result = {'application': app, 'version': manifest['version'], 'archive_sha256': digest, 'status': 'update_complete', 'services': status(app)['services']}
        receipt.write_text(json.dumps(result))
        receipt.chmod(0o600)
        return result


def install():
    if os.geteuid() != 0:
        raise ValueError('root_required')
    # No changes to sshd, firewall, passwords, services, application files or data.
    INSTALLED.parent.mkdir(parents=True, exist_ok=True)
    if Path(__file__).resolve() != INSTALLED:
        shutil.copyfile(__file__, INSTALLED)
    INSTALLED.chmod(0o755)
    os.chown(INSTALLED, 0, 0)
    folder = Path('/root/.ssh')
    if folder.is_symlink(): raise ValueError('ssh_directory_symlink')
    folder.mkdir(mode=0o700, exist_ok=True)
    keys = folder/'authorized_keys'
    if keys.is_symlink(): raise ValueError('authorized_keys_symlink')
    line = 'restrict,command="/usr/bin/python3 '+str(INSTALLED)+'" '+PUBLIC_KEY
    existing = keys.read_text() if keys.exists() else ''
    if line not in existing.splitlines():
        if PUBLIC_KEY.split()[1] in existing: raise ValueError('key_already_present_with_other_options')
        with keys.open('a') as f: f.write(('\n' if existing and not existing.endswith('\n') else '')+line+'\n')
    keys.chmod(0o600)
    os.chown(keys,0,0)
    print('ACCES MAINTENANCE ECMR ET TMS INSTALLE — TEST DE CONNEXION RESTANT A FAIRE')


def main():
    if sys.argv[1:] == ['--install']:
        install()
        return
    parts = command_parts(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
    app = parts[1]
    if parts[0] == 'deploy':
        value = deploy(app, parts[2], sys.stdin.buffer.read(MAX_ZIP+1))
    else:
        value = status(app) if parts[0] == 'status' else diagnose(app)
    print(json.dumps(value))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No raw Docker/app output, mail addresses, secrets or DB content in SSH logs.
        code = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z_]+', str(error)) else 'maintenance_failed'
        print(json.dumps({'status': 'failed', 'error': code}))
        sys.exit(1)

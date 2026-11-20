import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import server


class MaintenanceTests(unittest.TestCase):
    def archive(self, extra=None, app='tms'):
        files={'pilot_server.py':b'# fictitious runtime','Dockerfile.pilot':b'FROM scratch'}
        files.update(extra or {})
        manifest={'application':app,'version':'0.0','files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as z:
            for name,data in files.items():z.writestr(name,data)
            z.writestr('maintenance-manifest.json',json.dumps(manifest))
        value=raw.getvalue();return value,hashlib.sha256(value).hexdigest()

    def test_ssh_command_cannot_open_shell_or_other_host_paths(self):
        for command in ['','bash','sh -c id','status tms; id','status /opt','deploy ecmr ../x','status tms extra','scp -t /root','sftp']:
            with self.subTest(command=command),self.assertRaises(ValueError):server.command_parts(command)
        self.assertEqual(server.command_parts('status tms'),['status','tms'])

    def test_zip_rejects_configuration_secrets_path_traversal_and_symlinks(self):
        for name in ['../bad.py','/root/a.py','prototype/../../a.py','deploy/pilot.env','prototype/seal.key','prototype/.env','prototype/__pycache__/x.py','.ssh/authorized_keys','prototype\\bad.py']:
            raw,digest=self.archive({name:b'no'})
            with self.subTest(name=name),self.assertRaises(ValueError):server.unpack(raw,'tms',digest)
        raw,digest=self.archive();self.assertTrue(server.unpack(raw,'tms',digest)[1])
        with self.assertRaises(ValueError):server.unpack(raw,'tms','0'*64)

    def test_cross_application_package_is_refused(self):
        raw,digest=self.archive()
        with self.assertRaises(ValueError):server.unpack(raw,'ecmr',digest)

    def test_installer_preserves_existing_ssh_access_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ssh=root/'ssh';ssh.mkdir();keys=ssh/'authorized_keys';keys.write_text('existing-key\n')
            installed=root/'installed.py'
            original_path=server.Path
            def path(value):return ssh if str(value)=='/root/.ssh' else original_path(value)
            with patch.object(server,'INSTALLED',installed),patch.object(server,'Path',side_effect=path),patch.object(server.os,'geteuid',return_value=0),patch.object(server.os,'chown'):
                server.install();server.install()
            value=keys.read_text()
            self.assertTrue(value.startswith('existing-key\n'))
            self.assertEqual(value.count(server.PUBLIC_KEY),1)
            self.assertIn('restrict,command=',value)
            self.assertEqual(keys.stat().st_mode&0o777,0o600)

    def test_tms_failure_restores_source_and_previous_image(self):
        raw,digest=self.archive()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'pilot_server.py').write_bytes(b'old runtime');(root/'Dockerfile.pilot').write_bytes(b'old docker')
            commands=[]
            def run(args, app):
                from types import SimpleNamespace
                commands.append(args)
                if args[-3:]==['ps','-q','tms']:return SimpleNamespace(stdout=b'a'*64)
                if 'inspect' in args:return SimpleNamespace(stdout=b'sha256:old')
                if 'build' in args:raise RuntimeError('simulated build failure')
                return SimpleNamespace(stdout=b'')
            with patch.dict(server.ROOTS,{'tms':root}),patch.object(server,'run',side_effect=run):
                with self.assertRaises(RuntimeError):server.deploy('tms',digest,raw)
            self.assertEqual((root/'pilot_server.py').read_bytes(),b'old runtime')
            self.assertTrue(any('backup_host.py' in ' '.join(c) for c in commands))
            self.assertIn(['docker','image','tag','sha256:old','13urgent-tms:pilot'],commands)

    def test_repeat_deployment_does_not_repeat_migrations(self):
        raw,digest=self.archive()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'.maintenance';base.mkdir()
            (base/('applied-'+digest+'.json')).write_text(json.dumps({'status':'update_complete'}))
            with patch.dict(server.ROOTS,{'tms':root}),patch.object(server,'run') as run:
                self.assertTrue(server.deploy('tms',digest,raw)['already_applied']);run.assert_not_called()

if __name__=='__main__':unittest.main()

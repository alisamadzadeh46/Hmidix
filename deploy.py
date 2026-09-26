"""
Incremental deploy: upload only the files that changed since the last deploy.

An MD5 manifest stored in the user's home directory tracks what is already on
the server. Connection details are read from the environment (or the local
.env file) so no credentials live in the repository:

    DEPLOY_HOST, DEPLOY_PORT, DEPLOY_USER, DEPLOY_REMOTE_ROOT, DEPLOY_SERVICE
    DEPLOY_KEY_FILE   path to a private key (preferred), or
    DEPLOY_PASSWORD   password authentication as a fallback
    DEPLOY_TRUST_NEW_HOST
                      set to "true" once to accept and remember the server's
                      host key; afterwards unknown keys are rejected

Requires ``paramiko`` (a deploy-time dependency only).
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

LOCAL_ROOT = Path(__file__).resolve().parent
load_dotenv(LOCAL_ROOT / '.env')

HOST = os.environ.get('DEPLOY_HOST', '')
PORT = int(os.environ.get('DEPLOY_PORT', 22))
USER = os.environ.get('DEPLOY_USER', '')
KEY_FILE = os.environ.get('DEPLOY_KEY_FILE') or None
PASSWORD = os.environ.get('DEPLOY_PASSWORD') or None
REMOTE_ROOT = os.environ.get('DEPLOY_REMOTE_ROOT', '/var/www/hamidix').rstrip('/')
SERVICE = os.environ.get('DEPLOY_SERVICE', 'hamidix')
TRUST_NEW_HOST = os.environ.get('DEPLOY_TRUST_NEW_HOST', '').lower() in ('1', 'true', 'yes')
KNOWN_HOSTS = Path.home() / '.ssh' / 'known_hosts'
MANIFEST_PATH = Path.home() / '.deploy_manifest_hamidix.json'

SKIP_DIRS = {
    '.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea',
    'media', 'staticfiles', '_legacy',
}
SKIP_EXTS = {'.pyc', '.pyo'}
# Never overwrite the live database or server secrets from the local copy.
SKIP_FILES = {'db.sqlite3', '.env', 'shop_data.json'}


def md5(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def collect_files():
    files = {}
    for p in LOCAL_ROOT.rglob('*'):
        if p.is_dir():
            continue
        parts = p.relative_to(LOCAL_ROOT).parts
        if any(d in SKIP_DIRS for d in parts):
            continue
        if p.suffix in SKIP_EXTS:
            continue
        if p.name in SKIP_FILES:
            continue
        rel = p.relative_to(LOCAL_ROOT).as_posix()
        files[rel] = md5(p)
    return files


def load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest):
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def main():
    current = collect_files()
    previous = load_manifest()

    changed = {k: v for k, v in current.items() if previous.get(k) != v}
    deleted = [k for k in previous if k not in current]

    if not changed and not deleted:
        print('Nothing changed — server is up to date.')
        return

    if not HOST or not USER or not (KEY_FILE or PASSWORD):
        sys.exit('Set DEPLOY_HOST, DEPLOY_USER and DEPLOY_KEY_FILE or DEPLOY_PASSWORD.')

    print(f'Uploading {len(changed)} changed file(s)...')

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    # Refuse unknown servers (protects against man-in-the-middle attacks)
    # unless the first connection is explicitly trusted.
    if TRUST_NEW_HOST:
        KNOWN_HOSTS.parent.mkdir(mode=0o700, exist_ok=True)
        KNOWN_HOSTS.touch(mode=0o600, exist_ok=True)
        ssh.load_host_keys(str(KNOWN_HOSTS))
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        ssh.connect(HOST, PORT, USER, password=PASSWORD, key_filename=KEY_FILE, timeout=30)
    except paramiko.SSHException as exc:
        sys.exit(f'SSH connection failed: {exc}\n'
                 'For a new server, run once with DEPLOY_TRUST_NEW_HOST=true.')
    sftp = ssh.open_sftp()

    def remote_makedirs(remote_path):
        parts = remote_path.split('/')
        for i in range(2, len(parts) + 1):
            partial = '/'.join(parts[:i])
            try:
                sftp.stat(partial)
            except FileNotFoundError:
                sftp.mkdir(partial)

    for i, rel in enumerate(changed, 1):
        local_path = LOCAL_ROOT / rel
        remote_path = f'{REMOTE_ROOT}/{rel}'
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            remote_makedirs(remote_dir)
        print(f'  [{i}/{len(changed)}] {rel}')
        sftp.put(str(local_path), remote_path)

    sftp.close()

    # Apply DB migrations, refresh static files, then restart the app.
    post_cmds = [
        ('migrate',
         f'cd {REMOTE_ROOT} && PYTHONUTF8=1 venv/bin/python manage.py migrate --noinput'),
        ('collectstatic',
         f'cd {REMOTE_ROOT} && PYTHONUTF8=1 venv/bin/python manage.py collectstatic --noinput'),
        ('restart', f'systemctl restart {SERVICE}'),
    ]
    for label, cmd in post_cmds:
        print(f'Running {label}...')
        _, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if out:
            print('  ', out.splitlines()[-1])
        if err:
            print(f'  ({label} stderr):', err[-400:])

    ssh.close()

    new_manifest = dict(current)
    save_manifest(new_manifest)
    print(f'Done. Manifest saved to {MANIFEST_PATH}')


if __name__ == '__main__':
    main()

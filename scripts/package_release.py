"""Package an allowlisted release; never include local credentials or repository history."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parent.parent
files = [ROOT / name for name in ['Dockerfile', '.dockerignore', '.gitignore', 'render.yaml']]
files += [p for p in (ROOT / 'backend/base').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py', '.html', '.css', '.js'}]
files += [p for p in (ROOT / 'backend/backend').glob('*.py') if p.name != 'settings.py']
files += [ROOT / 'backend' / name for name in ['manage.py', 'render_start.py', 'requirements.txt', '.env.example']]
files += [p for folder in ['frontend/src', 'frontend/public'] for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix.lower() in {'.js', '.jsx', '.css', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico', '.woff', '.woff2', '.ttf'}]
files += [ROOT / 'frontend' / name for name in ['package.json', 'package-lock.json', 'vite.config.js', 'eslint.config.js', 'index.html']]
files += [p for p in (ROOT / 'scripts').glob('*') if p.suffix in {'.ps1', '.py'}]
files += [ROOT / 'docs' / name for name in ['FREE_HOSTING_ROLLOUT.md', 'GOOGLE_SIGN_IN_DEPLOYMENT.md', 'DEPLOYMENT.md']]
target = ROOT / 'artifacts/tipped-docker-release.zip'
target.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as output:
    for file in sorted(set(files)):
        output.write(file, file.relative_to(ROOT).as_posix())
with zipfile.ZipFile(target) as archive:
    names = archive.namelist()
    assert 'backend/backend/settings.py' not in names
    assert not any(n.endswith(('.env', '.dpapi', '.sqlite3')) or '/node_modules/' in n or '/private_media/' in n for n in names)
    assert 'backend/render_start.py' in names and 'scripts/verify-restore.ps1' in names
print(f'Packaged {len(names)} clean release files. SHA256 {hashlib.sha256(target.read_bytes()).hexdigest()}')

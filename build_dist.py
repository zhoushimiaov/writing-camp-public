# 生成 Cloudflare Pages 部署包（dist 文件夹，只含线上需要的静态文件）
# 用法：python build_dist.py
# 然后：npx wrangler pages deploy dist --project-name=writing-camp
# 或者直接把 dist 里的文件拖到 CF Pages 的「Upload assets」
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / 'dist'

# 部署需要的文件/文件夹（本地专用的 bat/py/证书/README 不上传）
INCLUDE = [
    'index.html',
    'style.css',
    'manifest.json',
    'sw.js',
    'js',
    'icons',
    'fonts',
]

if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()

for name in INCLUDE:
    src = ROOT / name
    dst = DIST / name
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

# 给线上版注入 CSP（源码不加：本地双击/单文件版不受限，审查设计层修复）
csp = ('<meta http-equiv="Content-Security-Policy" '
       "content=\"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; font-src 'self' data:; connect-src *; base-uri 'none'\">")
idx = DIST / 'index.html'
html = idx.read_text(encoding='utf-8')
if 'Content-Security-Policy' not in html:
    html = html.replace('<meta name="viewport"', csp + '\n<meta name="viewport"', 1)
    idx.write_text(html, encoding='utf-8')
    print('CSP 已注入 dist/index.html')

total = sum(f.stat().st_size for f in DIST.rglob('*') if f.is_file())
print('OK -> dist/ (%.1f MB)' % (total / 1024 / 1024))
print('下一步任选：')
print('  A. npx wrangler pages deploy dist --project-name=writing-camp')
print('  B. 打开 dash.cloudflare.com 的 Pages「Upload assets」，把 dist 里的内容拖进去')

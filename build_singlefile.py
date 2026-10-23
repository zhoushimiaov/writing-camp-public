# 把 index.html + style.css + js 打包成一个独立的单文件 HTML
# 并把「霞鹜文楷」按实际用到的字裁剪成子集、以 base64 内嵌（体积小，离线可用）
# 用途：AirDrop / 微信发到 iPad 存到「文件」里应急打开（正式使用推荐局域网方式）
import base64
import io
import pathlib
import string

ROOT = pathlib.Path(__file__).parent

# ---- 收集所有静态文字，用于裁剪字体 ----
text_parts = []
for f in ['index.html', 'style.css', 'js/data.js', 'js/app.js']:
    text_parts.append((ROOT / f).read_text(encoding='utf-8'))
all_text = ''.join(text_parts)
extra = string.printable + '。，！？：；、""\'\'（）《》〈〉【】·—…～¥％✓⬜★☆🎤📝👝✍️🕵️📣🌟🎉⭐✨🎊🏆⚔️🗡️🏦📚👑🐉🌱🧢🎓📜🎫🦊🐼🐯🐲🦁🐨🐸🦉'
seen = set()
text_parts = []
for ch in all_text + extra:
    if ch not in seen:
        seen.add(ch)
        text_parts.append(ch)
subset_text = ''.join(text_parts)


def font_base64(weight):
    from fontTools import subset
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.desubroutinize = True
    opts.layout_features = ['*']
    src = ROOT / 'fonts' / f'LXGWWenKai-{weight}.woff2'
    font = subset.load_font(str(src), opts)
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(text=subset_text)
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode('ascii')


html = (ROOT / 'index.html').read_text(encoding='utf-8')
css = (ROOT / 'style.css').read_text(encoding='utf-8')
data = (ROOT / 'js' / 'data.js').read_text(encoding='utf-8')
app = (ROOT / 'js' / 'app.js').read_text(encoding='utf-8')

# ---- 内嵌子集字体，替换掉外部字体引用 ----
for weight in ['Regular', 'Medium']:
    b64 = font_base64(weight)
    css = css.replace(
        f"url('fonts/LXGWWenKai-{weight}.woff2') format('woff2')",
        f"url(data:font/woff2;base64,{b64}) format('woff2')"
    )

html = html.replace('<link rel="stylesheet" href="style.css">',
                    '<style>\n' + css + '\n</style>')
html = html.replace('<script src="js/data.js"></script>',
                    '<script>\n' + data + '\n</script>')
html = html.replace('<script src="js/app.js"></script>',
                    '<script>\n' + app + '\n</script>')

out = ROOT / '写作小能手训练营-单文件版.html'
out.write_text(html, encoding='utf-8')
print('OK ->', out.name, f'({out.stat().st_size / 1024 / 1024:.1f} MB)')

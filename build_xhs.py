# 生成小红书小工具离线包（xhs/ 目录 + 可上传 zip）
# 用法：python build_xhs.py
# 改造原则（对照 .skill/minitool-zip-builder 各规范）：
#   1) 禁联网：移除 AI 批改/拍照认字（fetch 调用零残留）
#   2) 禁剪贴板/下载/prompt/SW：复制改长按选中文本、备份改粘贴导入、
#      重置门禁改双重 confirm、去掉 sw 注册与 storage.persist
#   3) 平台能力优先：作品卡用 canvas 画成图片 → saveImageToPhotosAlbum 保存
#      （无容器 API 时降级提示）；成就解锁调用 vibrateShort
#   4) Chrome 61 基线：flex gap 加 margin 兜底（行为检测）、grid 用 grid-gap、
#      inset 展开、ES2017 语法（源码本就满足）
#   5) 体积：字体按实际用字子集化，zip 目标 < 2MiB
import pathlib
import re
import zipfile

from fontTools import subset as fontsubset

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'xhs'

# ---------- 1. app.js 外科手术 ----------
app = (ROOT / 'js' / 'app.js').read_text(encoding='utf-8')


def cut(text, start, end, repl=''):
    """删除 [start, end) 之间的内容，start/end 均须唯一命中"""
    assert text.count(start) == 1, 'start 未唯一命中: ' + start[:40]
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[:i] + repl + text[j:]


def swap(text, old, new):
    assert text.count(old) == 1, '未唯一命中: ' + old[:60]
    return text.replace(old, new)


# 1.1 删除 AI 服务 + AI 批改两整节（fetch 零残留）
app = cut(app, "/* ================= AI 服务（智谱 / Agnes / Gemini",
          "/* ================= 头部 / 导航 ================= */")
# 1.2 migrateState 里的 AI 密钥字段迁移
app = cut(app, "  /* AI 字段迁移（老备份的 ocrKey → zhipuKey） */", "  return s;")
# 1.3 分享链接整节（?w= 只读卡 + 压缩解压 + b64）
app = cut(app, "/* ================= 分享链接（微信里点开就是只读作品卡） ================= */",
          "/* ================= 作品集 ================= */")

# 1.4 copyText → 长按复制弹窗（禁剪贴板）
app = swap(app, """function copyText(t, msg) {
  const done = () => toast(msg || '已复制 ✅');
  const fallback = () => {
    const ta = document.createElement('textarea');
    ta.value = t; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('复制失败，请手动选择复制'); }
    ta.remove();
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(t).then(done).catch(fallback);
  } else fallback();
}""", """/* 小红书容器禁用剪贴板 API：改为展示可选中文本，长按/全选后手动复制 */
function copyText(t, msg) {
  openModal(
    '<h2 class="center">📋 ' + esc(msg || '复制下面的内容') + '</h2>' +
    '<textarea id="copy-ta" rows="6" readonly>' + esc(t) + '</textarea>' +
    '<div class="q-btns"><button class="btn ghost small" data-act="copy-sel">📑 全选</button>' +
    '<button class="btn primary" data-act="modal-close">知道了</button></div>');
}""")

# 1.5 写作页：去掉拍照认字按钮/提示/文件选择
app = swap(app, """      '<div class="q-tools">' +
        '<button class="mini-btn" data-act="photo-ocr">📷 拍照认字</button>' +
        micHtml('co-text', '说') +
        '<span class="muted small">手写在纸上也行：点「📷 拍照认字」拍下来自动变成文字；键盘上的 🎤 也能说</span>' +
      '</div>' +
      '<input type="file" id="ocr-file" accept="image/*" capture="environment" style="display:none">' +
""", """      '<div class="q-tools">' +
        micHtml('co-text', '说') +
        '<span class="muted small">键盘上的 🎤 也能直接说话变文字哦</span>' +
      '</div>' +
""")

# 1.6 作品弹窗：去 AI 批改/分享链接/打印，加「保存作品卡图片」
app = swap(app, "    (w.ai ? aiSectionHtml(w.ai) : '') +\n", "")
app = swap(app, """      '<button class="btn primary" data-act="edit-work" data-id="' + w.id + '">✏️ 修改作文</button>' +
      '<button class="btn primary" data-act="ai-review" data-id="' + w.id + '">' + (w.ai ? '🤖 重新批改' : '🤖 请 AI 教练批改') + '</button>' +
""", """      '<button class="btn primary" data-act="save-card" data-id="' + w.id + '">🖼 保存作品卡图片</button>' +
      '<button class="btn ghost" data-act="edit-work" data-id="' + w.id + '">✏️ 修改作文</button>' +
""")
app = swap(app, """      '<button class="btn ghost" data-act="share-link" data-id="' + w.id + '">🔗 分享链接</button>' +
      '<button class="btn ghost" data-act="copy-work" data-plain="' + esc(copyStr) + '">📋 复制全文</button>' +
      '<button class="btn ghost" data-act="print-work">🖨 打印作品卡</button>' +
""", """      '<button class="btn ghost" data-act="copy-work" data-plain="' + esc(copyStr) + '">📋 复制全文</button>' +
""")

# 1.7 家长角：AI 设置区 → 小红书版说明
app = cut(app, "  '<section class=\"card\" id=\"sec-ocr\">",
          "  '<section class=\"card\"><h3 class=\"sec-t\">⚙️ 设置与数据</h3>' +",
          """  '<section class="card"><h3 class="sec-t">ℹ️ 小红书版说明</h3>' +
  '<p class="small">这一版<b>完全离线运行</b>：写作教练、训练营、成就图鉴、主题换色全部可用，作品能一键保存成图片，发到家庭群很方便。</p>' +
  '<p class="small muted">🤖 AI 批改和 📷 拍照认字需要联网，请用浏览器打开网页版：<b>writing.shimiao.work</b>（免费）。</p></section>' +

""")

# 1.8 备份按钮文案 + 去掉隐藏的 file input
app = swap(app, "'<button class=\"btn ghost\" data-act=\"exp-data\">⬇️ 导出备份</button>' +",
          "'<button class=\"btn ghost\" data-act=\"exp-data\">📋 导出备份（复制）</button>' +")
app = swap(app, "'<button class=\"btn ghost\" data-act=\"imp-data\">⬆️ 导入备份</button>' +",
          "'<button class=\"btn ghost\" data-act=\"imp-data\">📥 导入备份（粘贴）</button>' +")
app = swap(app, "  '<input type=\"file\" id=\"imp-file\" accept=\".json,application/json\" style=\"display:none\"></div>' +",
          "  '</div>' +")

# 1.9 事件处理器：删 OCR/AI/分享/打印相关 case
app = cut(app, "    case 'photo-ocr':", "    /* 作品 */")
app = cut(app, "    case 'ai-review': {", "    case 'copy-work':")
app = swap(app, "    case 'print-work': window.print(); break;",
          """    case 'save-card': {
      const w = kid().works.find(x => x.id === el.dataset.id);
      if (w && window.XhsCard) XhsCard.save(w, kid());
      else toast('当前环境不支持保存图片，请截图分享');
      break;
    }""")
app = swap(app, "    case 'imp-data': $('#imp-file').click(); break;",
          "    case 'imp-data': showImportModal(); break;")

# 1.10 exp-data → 弹窗展示 JSON（长按复制，替代下载）
app = cut(app, "    case 'exp-data': {", "    case 'imp-data':", """    case 'exp-data': {
      const clean = JSON.parse(JSON.stringify(S));
      clean.lastBackup = dateKey();
      S.lastBackup = dateKey(); save(); renderMain();
      openModal(
        '<h2 class="center">📋 导出备份</h2>' +
        '<p class="muted small center">长按选中下面的文字复制（或先点「全选」），存到备忘录 / 微信收藏，换设备时用「导入备份」粘贴回来</p>' +
        '<textarea id="exp-json" rows="10" readonly>' + esc(JSON.stringify(clean, null, 2)) + '</textarea>' +
        '<div class="q-btns"><button class="btn ghost small" data-act="exp-sel">📑 全选</button>' +
        '<button class="btn primary" data-act="modal-close">完成</button></div>');
      break;
    }
    case 'exp-sel': {
      const ta = $('#exp-json');
      if (ta) { ta.focus(); ta.select(); toast('已全选，长按文字即可复制'); }
      break;
    }
    case 'copy-sel': {
      const ta2 = $('#copy-ta');
      if (ta2) { ta2.focus(); ta2.select(); toast('已全选，长按文字即可复制'); }
      break;
    }
""")

# 1.11 重置门禁：prompt → 双重 confirm
app = swap(app, """      const a = 12 + Math.floor(Math.random() * 8);    /* 12-19 */
      const b = 3 + Math.floor(Math.random() * 6);     /* 3-8：乘法对小用户更费劲（审查 N4 修复） */
      const ans = prompt('⚠️ 家长确认：清空后所有孩子的作品、素材都会消失，不可恢复。\\n请输入 ' + a + ' × ' + b + ' 的答案继续：');
      if (ans === null) break;
      if (Number(ans) !== a * b) { toast('答案不对，已取消'); break; }
""", """      if (!confirm('⚠️ 家长确认：清空后所有孩子的作品、素材都会消失，不可恢复。\\n确定要继续吗？')) break;
      if (!confirm('再想一下：真的要全部清空吗？此操作无法撤销！')) break;
""")

# 1.12 change 事件监听（ocr-file / imp-file 分支全没了）整段删除
app = cut(app, "document.addEventListener('change', e => {", "document.addEventListener('keydown'")

# 1.13 粘贴导入弹窗 + 处理器（追加在事件监听之前）
app = swap(app, "/* ================= 事件 ================= */", """/* ================= 小红书版：粘贴导入备份 ================= */
function showImportModal() {
  openModal(
    '<h2 class="center">📥 导入备份</h2>' +
    '<p class="muted small center">把之前导出的备份文字完整粘贴到下面，再点「导入」</p>' +
    '<textarea id="imp-json" rows="8" placeholder="把备份文字完整粘贴到这里…"></textarea>' +
    '<div class="q-btns"><button class="btn ghost" data-act="modal-close">取消</button>' +
    '<button class="btn primary" data-act="imp-paste">导入</button></div>');
}

/* ================= 事件 ================= */""")
app = swap(app, "    case 'copy-work': copyText(el.dataset.plain, '📋 全文已复制，去粘贴给家人吧！'); break;",
          """    case 'copy-work': copyText(el.dataset.plain, '复制全文，去粘贴给家人吧'); break;
    case 'imp-paste': {
      const raw = ($('#imp-json') || {}).value || '';
      if (!raw.trim()) { toast('先粘贴备份内容呀'); break; }
      try {
        const data = migrateState(JSON.parse(raw));
        if (!data) throw new Error('bad');
        if (!confirm('导入备份会覆盖本机上所有孩子现在保存的全部数据（作品、素材、XP）。\\n确定继续吗？')) break;
        S = data;
        S.lastBackup = dateKey();
        save(); closeModal(); render();
        toast('备份导入成功 ✅');
      } catch (err) { toast('备份内容不对，导入失败（要完整粘贴哦）'); }
      break;
    }""")

# 1.14 启动流程：去 ?w= 分享分支 + sw 注册 + storage.persist
app = cut(app, "/* 带 ?w= 分享参数时：只显示只读作品卡（微信里打开的样子） */",
          "/* iPad/PWA：在安全上下文（https 或本机）注册离线缓存；",
          """render();
if (!S.onboarded) showOnboarding();
""")
app = swap(app, """
/* iPad/PWA：在安全上下文（https 或本机）注册离线缓存；
   单文件版和普通 file:// 打开时自动跳过 */
if ('serviceWorker' in navigator &&
    (location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(location.hostname))) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
""", "\n")
app = swap(app, "if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});\napplyTheme();", "applyTheme();")

# 1.15 成就解锁 / 交卷成功 → 轻震一下（平台能力，无则静默）
app = swap(app, "  const b = achQueue.shift();\n  confetti(22);",
          "  const b = achQueue.shift();\n  confetti(22);\n  if (window.XhsBridge) XhsBridge.haptic();")
app = swap(app, "  missionBonus();   /* 交卷计入当日任务（审查 C1 修复） */\n  confetti(36);",
          "  missionBonus();   /* 交卷计入当日任务（审查 C1 修复） */\n  confetti(36);\n  if (window.XhsBridge) XhsBridge.haptic();")

# 1.16 版本标识
app = swap(app, "const APP_VERSION = 'v1.2';", "const APP_VERSION = 'v1.2-xhs';")

(OUT / 'js').mkdir(parents=True, exist_ok=True)
(OUT / 'fonts').mkdir(parents=True, exist_ok=True)
(OUT / 'js' / 'app.js').write_text(app, encoding='utf-8')

# ---------- 2. data.js 原样 ----------
(OUT / 'js' / 'data.js').write_text((ROOT / 'js' / 'data.js').read_text(encoding='utf-8'), encoding='utf-8')

# ---------- 3. style.css：Chrome 61 兼容变换 ----------
css = (ROOT / 'style.css').read_text(encoding='utf-8')
# 3.1 inset 展开（Chrome 61 无 inset 简写）
n_inset = css.count('inset: 0;')
assert n_inset >= 2, 'inset 出现次数异常: %d' % n_inset
css = css.replace('inset: 0;', 'top: 0; right: 0; bottom: 0; left: 0;')
# 3.2 grid 的 gap → grid-gap 兜底
companion = ['\n/* ===== 小红书容器：Chrome 61 基线兜底（flex gap 用 margin、grid 补 grid-gap） ===== */\n']
out_lines = []
for line in css.split('\n'):
    if 'gap:' in line and 'display: grid' in line:
        m = re.search(r'gap:\s*([\d.]+)px', line)
        if m:
            line = line.replace('gap: ' + m.group(1) + 'px', 'grid-gap: ' + m.group(1) + 'px; gap: ' + m.group(1) + 'px', 1)
    out_lines.append(line)
    # flex gap → 行为检测出 no-flex-gap 时用 margin 兜底
    if 'gap:' in line and ('display: flex' in line or 'display:flex' in line or 'display: inline-flex' in line or 'display:inline-flex' in line):
        m = re.search(r'gap:\s*([\d.]+)px', line)
        if m and '{' in line and '}' in line:
            g = m.group(1)
            sel = line.split('{')[0].strip()
            col = 'flex-direction: column' in line or 'flex-direction:column' in line
            wrap = 'flex-wrap: wrap' in line or 'flex-wrap:wrap' in line
            if col:
                companion.append('html.no-flex-gap %s > * + * { margin-top: %spx; }' % (sel, g))
            else:
                # 行方向（含 wrap）：兄弟项间距用 margin-left 兜底，不碰父级 margin 避免覆盖原布局
                companion.append('html.no-flex-gap %s > * + * { margin-left: %spx; }' % (sel, g))
css = '\n'.join(out_lines)
css += '\n'.join(companion)
# 3.3 移动端：点按高亮、安全区
css += """
/* ===== 小红书容器：触摸与安全区 ===== */
body { -webkit-tap-highlight-color: transparent; }
#main { padding-bottom: 80px; padding-bottom: calc(80px + var(--safe-area-inset-bottom, env(safe-area-inset-bottom, 0px))); }
"""
(OUT / 'style.css').write_text(css, encoding='utf-8')

# ---------- 4. 字体子集化（体积门禁） ----------
all_text = '\n'.join([
    (OUT / 'js' / 'app.js').read_text(encoding='utf-8'),
    (OUT / 'js' / 'data.js').read_text(encoding='utf-8'),
    (OUT / 'style.css').read_text(encoding='utf-8'),
])
import string as _string
extra = _string.printable + '。，！？：；、""''（）《》〈〉【】·—…～¥％✓⬜★☆🎤📝👝✍️🕵️📣🌟🎉⭐✨🎊🏆⚔️🗡️🏦📚👑🐉🌱🧢🎓📜🎫🦊🐼🐯🐲🦁🐨🐸🦉🎨⚖️🔎🎤🖼📑📋📥❌✅'
seen = set()
subset_text = ''.join(c for c in (all_text + extra) if not (c in seen or seen.add(c)))

for weight in ['Regular', 'Medium']:
    opts = fontsubset.Options()
    opts.flavor = 'woff2'
    opts.desubroutinize = True
    opts.layout_features = ['*']
    font = fontsubset.load_font(str(ROOT / 'fonts' / f'LXGWWenKai-{weight}.woff2'), opts)
    sub = fontsubset.Subsetter(options=opts)
    sub.populate(text=subset_text)
    sub.subset(font)
    font.save(str(OUT / 'fonts' / f'LXGWWenKai-{weight}.woff2'))
    print('字体子集', weight, round((OUT / 'fonts' / f'LXGWWenKai-{weight}.woff2').stat().st_size / 1024), 'KB')

# ---------- 5. xhs-bridge.js（容器能力桥 + flex gap 行为检测） ----------
bridge = """/* 小红书小工具桥：容器能力检测 + flex gap 行为检测 + 作品卡保存 */
'use strict';
window.__XHS__ = true;
(function () {
  /* Chrome 61 不支持 flex gap：实测布局行为，不支持时加 no-flex-gap 走 margin 兜底 */
  try {
    var fl = document.createElement('div');
    fl.style.position = 'absolute';
    fl.style.visibility = 'hidden';
    fl.style.display = 'flex';
    fl.style.flexDirection = 'column';
    fl.style.rowGap = '1px';
    fl.appendChild(document.createElement('div'));
    fl.appendChild(document.createElement('div'));
    document.body.appendChild(fl);
    var ok = fl.scrollHeight === 1;
    fl.parentNode.removeChild(fl);
    if (!ok) document.documentElement.className += ' no-flex-gap';
  } catch (e) { document.documentElement.className += ' no-flex-gap'; }
})();

window.XhsBridge = {
  haptic: function () {
    try {
      var m = window.xhs && window.xhs.miniTool;
      if (m && typeof m.vibrateShort === 'function') {
        var r = m.vibrateShort({ type: 'light' });
        if (r && r.catch) r.catch(function () {});
      }
    } catch (e) { /* 无振动能力则静默 */ }
  }
};

/* 作品卡 → canvas → 保存到相册（saveImageToPhotosAlbum；无容器 API 时提示截图） */
window.XhsCard = {
  save: function (w, k) {
    var mt = window.xhs && window.xhs.miniTool;
    var self = this;
    toast('正在生成图片…');
    this._render(w, k).then(function (dataUrl) {
      if (!mt || typeof mt.saveImageToPhotosAlbum !== 'function') {
        window.toast('当前环境不支持保存到相册，请截屏分享 📱');
        return;
      }
      var done = function () { window.toast('🖼 作品卡已存入相册！去发家庭群吧'); };
      var fail = function (e) {
        var msg = e && e.errMsg ? String(e.errMsg) : '';
        if (msg.indexOf('auth') >= 0 || msg.indexOf('deny') >= 0) window.toast('相册权限被拒绝了，去设置里打开试试');
        else window.toast('保存失败，请截屏分享');
      };
      if (typeof mt.writeTempFile === 'function') {
        mt.writeTempFile({ data: dataUrl }).then(function (res) {
          mt.saveImageToPhotosAlbum({ filePath: res.filePath }).then(done).catch(fail);
        }).catch(function () { mt.saveImageToPhotosAlbum({ filePath: dataUrl }).then(done).catch(fail); });
      } else {
        mt.saveImageToPhotosAlbum({ filePath: dataUrl }).then(done).catch(fail);
      }
    }).catch(function () { window.toast('图片生成失败'); });
  },
  _rr: function (ctx, x, y, w2, h2, r) {   /* roundRect（Chrome 61 无内置） */
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w2, y, x + w2, y + h2, r);
    ctx.arcTo(x + w2, y + h2, x, y + h2, r);
    ctx.arcTo(x, y + h2, x, y, r);
    ctx.arcTo(x, y, x + w2, y, r);
    ctx.closePath();
  },
  _svgImg: function (svg) {
    return new Promise(function (res, rej) {
      var img = new Image();
      var url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
      img.onload = function () { URL.revokeObjectURL(url); res(img); };
      img.onerror = function () { URL.revokeObjectURL(url); rej(new Error('svg')); };
      img.src = url;
    });
  },
  _render: function (w, k) {
    var W = 750, PAD = 56, self = this;
    var mFont = '28px "LXGW WenKai", "Kaiti SC", "KaiTi", sans-serif';
    var meas = document.createElement('canvas').getContext('2d');
    meas.font = mFont;
    var maxW = W - PAD * 2;
    var lines = [];
    var para = String(w.text || '').split('\\n');
    for (var pi = 0; pi < para.length; pi++) {
      var cur = '';
      for (var ci = 0; ci < para[pi].length; ci++) {
        var test = cur + para[pi][ci];
        if (meas.measureText(test).width > maxW && cur) { lines.push(cur); cur = para[pi][ci]; }
        else cur = test;
      }
      lines.push(cur);
    }
    var H = PAD + 120 + (w.best ? 110 : 0) + lines.length * 46 + 190 + PAD;
    var cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    var c = cv.getContext('2d');
    c.fillStyle = '#FFFDF8';
    c.fillRect(0, 0, W, H);
    c.lineWidth = 6; c.strokeStyle = '#5C5266';
    self._rr(c, 16, 16, W - 32, H - 32, 28); c.stroke();
    c.fillStyle = '#5C5266'; c.textAlign = 'center';
    c.font = 'bold 40px "LXGW WenKai", "Kaiti SC", "KaiTi", sans-serif';
    c.fillText('《' + w.title + '》', W / 2, PAD + 52);
    c.font = '24px "LXGW WenKai", sans-serif';
    c.fillStyle = '#8A7F96';
    c.fillText(k.avatar + ' ' + k.name + ' · ' + k.grade + ' · ' + w.date + ' · ' + w.chars + ' 字', W / 2, PAD + 96);
    var y = PAD + 150;
    if (w.best) {
      c.fillStyle = '#FFF6DE';
      self._rr(c, PAD - 10, y - 36, maxW + 20, 92, 14); c.fill();
      c.strokeStyle = '#F9DC8F'; c.lineWidth = 3; c.stroke();
      c.fillStyle = '#6B5313'; c.font = 'bold 26px "LXGW WenKai", sans-serif';
      c.fillText('🌟 金句', W / 2, y - 4);
      c.font = '26px "LXGW WenKai", sans-serif';
      var bl = w.best.length > 22 ? w.best.slice(0, 22) + '…' : w.best;
      c.fillText('“' + bl + '”', W / 2, y + 34);
      y += 110;
    }
    c.textAlign = 'left';
    c.fillStyle = '#5C5266';
    c.font = mFont;
    for (var i = 0; i < lines.length; i++) c.fillText(lines[i], PAD, y + i * 46);
    var mascotP = self._svgImg(window.mascot(MASCOT_COACH, 96));
    return mascotP.then(function (img) {
      c.drawImage(img, W - PAD - 96, H - PAD - 150, 96, 96);
      c.textAlign = 'center';
      c.fillStyle = '#8A7F96';
      c.font = '22px "LXGW WenKai", sans-serif';
      c.fillText('来自「写作小能手训练营」', W / 2, H - PAD - 14);
      return cv.toDataURL('image/png');
    }, function () {
      c.textAlign = 'center';
      c.fillStyle = '#8A7F96';
      c.font = '22px "LXGW WenKai", sans-serif';
      c.fillText('来自「写作小能手训练营」', W / 2, H - PAD - 14);
      return cv.toDataURL('image/png');
    });
  }
};
"""
(OUT / 'js' / 'xhs-bridge.js').write_text(bridge, encoding='utf-8')

# ---------- 6. index.html（容器模板规范） ----------
html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#FDF7F3">
<title>写作小能手训练营</title>
<link rel="stylesheet" href="./style.css">
</head>
<body>
<header id="topbar"></header>
<nav id="tabs"></nav>
<main id="main"></main>
<div id="fx"></div>
<div id="toast"></div>
<div id="modal-root"></div>
<script src="./js/xhs-bridge.js"></script>
<script src="./js/data.js"></script>
<script src="./js/app.js"></script>
</body>
</html>
"""
(OUT / 'index.html').write_text(html, encoding='utf-8')

# ---------- 7. 打包（压缩目录内容，index.html 在 zip 根） ----------
zip_path = ROOT / '写作小能手训练营-小红书小工具.zip'
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in sorted(OUT.rglob('*')):
        if f.is_file():
            z.write(f, f.relative_to(OUT).as_posix())

total = sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file())
print('OK -> xhs/ (%.2f MB 源) + %s (%.2f MB zip)' % (total / 1048576, zip_path.name, zip_path.stat().st_size / 1048576))

# 写作小能手训练营 · 局域网服务器
# 在电脑上运行：iPad 用 Safari 打开下面打印的网址即可（需同一 Wi-Fi）
# 文件夹里有 cert.pem/key.pem 时会同时开 HTTPS（端口 +1），iPad 上用 https 网址
# 才能使用页面内的 🎙️ 语音识别按钮；键盘自带的听写任何方式都能用
import http.server
import os
import socket
import socketserver
import ssl
import sys
import threading

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PORT = 8642

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.html': 'text/html; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.js': 'text/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.webmanifest': 'application/manifest+json; charset=utf-8',
    }

    # 局域网安全：改用白名单，只放行前端静态资源（审查 N6 修复）
    def _denied(self):
        from urllib.parse import unquote
        path = unquote(self.path.split('?')[0])
        if path.startswith('/.') or '/.' in path:
            return True                      # 隐藏目录/文件（.wrangler 等）
        if path.endswith('/'):
            return path != '/'               # 只开放根目录，其余目录一律 403
        base = os.path.basename(path.lower())
        if base in ('cf-token.txt', 'key.pem', 'cert.pem'):
            return True                      # 双保险：名单内文件永不放行
        ext = os.path.splitext(base)[1]
        return ext not in ('.html', '.css', '.js', '.mjs', '.json',
                           '.png', '.jpg', '.jpeg', '.svg', '.ico',
                           '.woff2', '.webmanifest', '.webp', '.txt')

    def send_head(self):
        if self._denied():
            self.send_error(403, 'Forbidden')
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # 不刷屏


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


ip = lan_ip()
has_cert = os.path.exists('cert.pem') and os.path.exists('key.pem')
print('=' * 56)
print()
print('   ✒️  写作小能手训练营 · 局域网服务器已启动')
print()
print(f'   在这台电脑上打开 :  http://127.0.0.1:{PORT}/')
print(f'   在 iPad 上打开   :  http://{ip}:{PORT}/')
if has_cert:
    print(f'   🎤 语音识别专用  :  https://{ip}:{PORT + 1}/')
print()
print('   ① 确认 iPad 和这台电脑连的是同一个 Wi-Fi')
print(f'   ② 用 iPad 的 Safari 打开  http://{ip}:{PORT}/')
if has_cert:
    print('      （想用页面里的 🎙️ 语音按钮，就改用上面的 https 网址，')
    print('       第一次打开会提示证书警告：点「显示详细信息」→「访问此网站」）')
print('   ③ 点 Safari 的「分享」→「添加到主屏幕」')
print('      以后从主屏幕图标点开，就像装了个 App')
print('   ④ 用完在当前窗口按 Ctrl+C 关闭服务器')
print()
print('=' * 56)

try:
    if has_cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain('cert.pem', 'key.pem')
        httpsd = Server(('', PORT + 1), Handler)
        httpsd.socket = ctx.wrap_socket(httpsd.socket, server_side=True)
        threading.Thread(target=httpsd.serve_forever, daemon=True).start()

    with Server(('', PORT), Handler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print('\n服务器已关闭，再见！')
except OSError as e:
    print(f'\n端口被占用了（可能已经开过一个服务器）。')
    print('直接用 iPad 打开上面的网址就行；或重启电脑后再试。')
    input('按回车键退出…')

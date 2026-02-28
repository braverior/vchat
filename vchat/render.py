import re
import threading

from vchat.styles import S, get_terminal_width


class StreamRenderer:
    """逐行缓冲 + 渲染的流式 Markdown 输出器。
    token 到达后先进缓冲区，凑满一行立即渲染输出。"""

    INDENT = "  "

    def __init__(self):
        self._buf = ""
        self._in_code = False
        self._started = False

    def feed(self, token):
        """喂入一个流式 token"""
        self._buf += token
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self._print_line(line)

    def flush(self):
        """流结束后，将缓冲区余量输出"""
        if self._buf:
            self._print_line(self._buf)
            self._buf = ""
        print()

    def _print_line(self, line):
        rendered = self._render_line(line)
        print(f"{self.INDENT}{rendered}{S.RST}")
        self._started = True

    def _render_line(self, line):
        # 代码块围栏 ```
        if line.strip().startswith('```'):
            w = min(get_terminal_width() - 6, 72)
            if not self._in_code:
                self._in_code = True
                lang = line.strip()[3:].strip()
                label = f" {lang} " if lang else ""
                return f"{S.DIM}{S.CYAN}{'─' * 2}{label}{'─' * max(1, w - 2 - len(label))}{S.RST}"
            else:
                self._in_code = False
                return f"{S.DIM}{S.CYAN}{'─' * w}{S.RST}"

        # 代码块内容
        if self._in_code:
            return f"{S.CYAN}{line}{S.RST}"

        # 标题
        m = re.match(r'^(#{1,3})\s+(.*)', line)
        if m:
            lvl, title = len(m.group(1)), m.group(2)
            if lvl == 1:
                return f"\n{S.BOLD}{S.MAGENTA}▎ {self._inline(title)}{S.RST}"
            elif lvl == 2:
                return f"\n{S.BOLD}{S.BLUE}{self._inline(title)}{S.RST}"
            else:
                return f"{S.BOLD}{S.CYAN}{self._inline(title)}{S.RST}"

        # 水平线
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            w = min(get_terminal_width() - 6, 56)
            return f"{S.DIM}{'─' * w}{S.RST}"

        # 无序列表
        m = re.match(r'^(\s*)[*\-+]\s+(.*)', line)
        if m:
            indent = m.group(1)
            return f"{indent}{S.CYAN}•{S.RST} {self._inline(m.group(2))}"

        # 有序列表
        m = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
        if m:
            indent = m.group(1)
            return f"{indent}{S.CYAN}{m.group(2)}.{S.RST} {self._inline(m.group(3))}"

        # 引用块
        if line.strip().startswith('>'):
            content = self._inline(line.strip()[1:].strip())
            return f"{S.DIM}{S.GREEN}▏{S.RST} {S.ITALIC}{content}{S.RST}"

        # 普通行
        return self._inline(line)

    @staticmethod
    def _inline(text):
        text = re.sub(r'`([^`]+)`', f'{S.CYAN}{S.DIM}\\1{S.RST}', text)
        text = re.sub(r'\*\*\*(.+?)\*\*\*', f'{S.BOLD}{S.ITALIC}\\1{S.RST}', text)
        text = re.sub(r'\*\*(.+?)\*\*', f'{S.BOLD}\\1{S.RST}', text)
        text = re.sub(r'\*(.+?)\*', f'{S.ITALIC}\\1{S.RST}', text)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', f'{S.ULINE}{S.BLUE}\\1{S.RST}{S.DIM} (\\2){S.RST}', text)
        return text


class Spinner:
    """在等待 API 响应时显示思考动画"""

    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, label="思考中"):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        print(f'\r\033[K', end='', flush=True)

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            elapsed = i * 0.1
            print(f'\r  {S.DIM}{S.CYAN}{frame} {self.label} {elapsed:.1f}s{S.RST}', end='', flush=True)
            self._stop.wait(0.1)
            i += 1

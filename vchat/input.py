import os
import sys
import select

try:
    import tty
    import termios
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False


class InputReader:
    """自定义输入：Shift+Tab 无痕检测、行编辑、历史记录，配合 Screen 固定底栏"""

    def __init__(self):
        self.history = []
        self._hist_pos = 0
        self._saved_buf = None

    def read(self, screen, on_shift_tab=None):
        if not _HAS_TERMIOS:
            return input("❯ ")

        screen.to_input()

        fd = sys.stdin.fileno()
        old_attrs = termios.tcgetattr(fd)
        buf = []
        self._hist_pos = len(self.history)
        self._saved_buf = None

        try:
            tty.setcbreak(fd)
            while True:
                ch = _read_char(fd)

                # ── Escape 序列 ──
                if ch == '\x1b':
                    seq = _read_escape_seq(fd)
                    if seq == '[Z':  # Shift+Tab
                        if on_shift_tab:
                            on_shift_tab()
                        screen.update_status()
                        screen.redraw_input(buf)
                    elif seq == '[A':  # ↑
                        self._hist_prev(buf)
                        screen.redraw_input(buf)
                    elif seq == '[B':  # ↓
                        self._hist_next(buf)
                        screen.redraw_input(buf)
                    continue

                # ── 回车 ──
                if ch in ('\r', '\n'):
                    line = ''.join(buf)
                    if line.strip():
                        self.history.append(line)
                    screen.clear_input()
                    return line

                # ── 退格 ──
                if ch in ('\x7f', '\x08'):
                    if buf:
                        w = _char_width(buf.pop())
                        sys.stdout.write('\b \b' * w)
                        sys.stdout.flush()
                    continue

                # ── Ctrl+C ──
                if ch == '\x03':
                    raise KeyboardInterrupt

                # ── Ctrl+D ──
                if ch == '\x04':
                    if not buf:
                        raise EOFError
                    continue

                # ── Ctrl+U 清行 ──
                if ch == '\x15':
                    buf.clear()
                    screen.redraw_input(buf)
                    continue

                # ── Ctrl+W 删词 ──
                if ch == '\x17':
                    while buf and buf[-1] == ' ':
                        buf.pop()
                    while buf and buf[-1] != ' ':
                        buf.pop()
                    screen.redraw_input(buf)
                    continue

                # ── Tab 忽略 ──
                if ch == '\t':
                    continue

                # ── 可打印字符 ──
                if ord(ch) >= 32:
                    buf.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)

    def _hist_prev(self, buf):
        if not self.history or self._hist_pos <= 0:
            return
        if self._hist_pos == len(self.history):
            self._saved_buf = list(buf)
        self._hist_pos -= 1
        buf.clear()
        buf.extend(list(self.history[self._hist_pos]))

    def _hist_next(self, buf):
        if self._hist_pos >= len(self.history):
            return
        self._hist_pos += 1
        buf.clear()
        if self._hist_pos == len(self.history):
            if self._saved_buf is not None:
                buf.extend(self._saved_buf)
        else:
            buf.extend(list(self.history[self._hist_pos]))


# ── 底层读取 ─────────────────────────────────────────────────────────

def _read_char(fd):
    """从 fd 读一个完整 UTF-8 字符"""
    b = os.read(fd, 1)
    if not b:
        raise EOFError
    first = b[0]
    if first < 0x80:
        return b.decode('utf-8')
    if first < 0xC0:
        return b.decode('utf-8', errors='replace')
    remaining = 1 if first < 0xE0 else (2 if first < 0xF0 else 3)
    for _ in range(remaining):
        b += os.read(fd, 1)
    return b.decode('utf-8', errors='replace')


def _read_escape_seq(fd):
    """读取转义序列后续字节"""
    seq = ''
    while select.select([fd], [], [], 0.05)[0]:
        b = os.read(fd, 1)
        if not b:
            break
        c = b.decode('utf-8', errors='replace')
        seq += c
        if c.isalpha() or c == '~':
            break
    return seq


def _char_width(ch):
    """字符显示宽度（CJK 宽字符返回 2）"""
    code = ord(ch)
    if (0x1100 <= code <= 0x115F or
        0x2E80 <= code <= 0x303F or
        0x3040 <= code <= 0x33BF or
        0x3400 <= code <= 0x4DBF or
        0x4E00 <= code <= 0x9FFF or
        0xA000 <= code <= 0xA4CF or
        0xAC00 <= code <= 0xD7AF or
        0xF900 <= code <= 0xFAFF or
        0xFE10 <= code <= 0xFE6F or
        0xFF01 <= code <= 0xFF60 or
        0xFFE0 <= code <= 0xFFE6 or
        0x20000 <= code <= 0x2FA1F or
        0x30000 <= code <= 0x3134F):
        return 2
    return 1

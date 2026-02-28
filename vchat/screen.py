import sys
import shutil

from vchat.styles import S


class Screen:
    """固定底部输入栏 + 上方滚动区"""

    BOTTOM = 4  # 分隔线 + 输入行 + 分隔线 + 状态栏

    def __init__(self):
        self.web_enabled = False
        self.model = ""
        self._active = False
        self._update_size()

    def _update_size(self):
        c, r = shutil.get_terminal_size((80, 24))
        self.w = c
        self.h = r

    # ── 生命周期 ──

    def setup(self, model, web_enabled):
        self.model = model
        self.web_enabled = web_enabled
        self._active = True
        self._update_size()
        sys.stdout.write('\033[2J\033[H')           # 清屏
        sys.stdout.write(f'\033[1;{self.h - self.BOTTOM}r')  # 设置滚动区
        self._draw_bar()
        sys.stdout.write('\033[1;1H')               # 光标回滚动区顶部
        sys.stdout.flush()

    def cleanup(self):
        if not self._active:
            return
        self._active = False
        sys.stdout.write(f'\033[1;{self.h}r')       # 重置滚动区
        sys.stdout.write(f'\033[{self.h};1H\n')
        sys.stdout.flush()

    # ── 底部栏绘制 ──

    def _draw_bar(self):
        h, w = self.h, self.w
        sep = f'{S.DIM}{"─" * w}{S.RST}'
        sys.stdout.write(f'\033[{h-3};1H\033[2K{sep}')
        sys.stdout.write(f'\033[{h-2};1H\033[2K{S.BOLD}❯{S.RST} ')
        sys.stdout.write(f'\033[{h-1};1H\033[2K{sep}')
        sys.stdout.write(f'\033[{h};1H\033[2K')
        self._write_status()

    def _write_status(self):
        if self.web_enabled:
            web = f'{S.CYAN}● 联网{S.RST}'
        else:
            web = f'{S.DIM}○ 离线{S.RST}'
        sys.stdout.write(f'{web}  模型：{S.BOLD}{self.model}{S.RST}')

    def update_status(self):
        """刷新状态栏（用 ANSI save/restore 保持调用方光标不变）"""
        sys.stdout.write('\033[s')
        sys.stdout.write(f'\033[{self.h};1H\033[2K')
        self._write_status()
        sys.stdout.write('\033[u')
        sys.stdout.flush()

    # ── 输入行操作 ──

    def to_input(self):
        sys.stdout.write(f'\033[{self.h - 2};3H')
        sys.stdout.flush()

    def clear_input(self):
        sys.stdout.write(f'\033[{self.h - 2};1H\033[2K{S.BOLD}❯{S.RST} ')
        sys.stdout.flush()

    def redraw_input(self, buf):
        text = ''.join(buf)
        sys.stdout.write(f'\033[{self.h - 2};1H\033[2K{S.BOLD}❯{S.RST} {text}')
        sys.stdout.flush()

    # ── 滚动区操作 ──

    def to_scroll(self):
        """光标移至滚动区末行（输出内容用）"""
        sys.stdout.write(f'\033[{self.h - self.BOTTOM};1H')
        sys.stdout.flush()

import sys
import readline  # noqa: F401 — 提供更好的输入体验（历史记录等）

from vchat.styles import S, get_terminal_width
from vchat.config import ConfigManager
from vchat.chat import ChatSession


def print_help():
    cmds = [
        ("/model <name>",  "切换模型"),
        ("/models",        "列出所有可用模型"),
        ("/web",           "切换联网模式"),
        ("/search <query>","手动搜索 (不发送给AI)"),
        ("/fetch <url>",   "获取指定网页内容"),
        ("/clear",         "清空对话历史"),
        ("/history",       "显示当前对话历史"),
        ("/help",          "显示此帮助信息"),
        ("/quit",          "退出程序"),
    ]
    print()
    print(f"  {S.BOLD}命令列表{S.RST}")
    print(f"  {S.DIM}{'─' * 44}{S.RST}")
    for cmd, desc in cmds:
        print(f"  {S.CYAN}{cmd:<20}{S.RST} {S.DIM}{desc}{S.RST}")
    print()
    print(f"  {S.DIM}提示: 行末输入 \\ 可续行输入多行文本{S.RST}")
    print()


def print_banner(session):
    w = min(get_terminal_width(), 56)
    web_icon = f"{S.CYAN}●{S.RST}" if session.web_enabled else f"{S.DIM}○{S.RST}"
    web_text = "联网" if session.web_enabled else "离线"

    print()
    print(f"  {S.BOLD}{S.CYAN}vchat{S.RST}{S.DIM} — AI Chat{S.RST}")
    print(f"  {S.DIM}{'─' * (w - 4)}{S.RST}")
    print(f"  {S.DIM}模型{S.RST}  {S.BOLD}{session.model}{S.RST}")
    print(f"  {S.DIM}联网{S.RST}  {web_icon} {web_text}")
    print(f"  {S.DIM}{'─' * (w - 4)}{S.RST}")
    print(f"  {S.DIM}输入 /help 查看命令 · /web 开启联网 · /quit 退出{S.RST}")
    print()


# ── 子命令处理 ────────────────────────────────────────────────────────

def handle_config(config, args):
    """处理 vchat config [set <key> <value>]"""
    if not args:
        config.show()
        return
    if args[0] == "set" and len(args) >= 3:
        config.set(args[1], args[2])
    elif args[0] == "set":
        print(f"  {S.DIM}用法: vchat config set <key> <value>{S.RST}")
        print(f"  {S.DIM}可选 key: api_key, base_url, model{S.RST}")
    else:
        config.show()


def handle_models(config, args):
    """处理 vchat models [set <name>]"""
    session = ChatSession(config)
    if args and args[0] == "set" and len(args) >= 2:
        session.set_model(args[1], persist=True)
        return
    if args and args[0] == "set":
        print(f"  {S.DIM}用法: vchat models set <model_name>{S.RST}")
        return
    session.list_models()


# ── REPL 循环 ─────────────────────────────────────────────────────────

def repl(session):
    """交互式 REPL 循环"""
    print_banner(session)

    while True:
        try:
            web_dot = f"{S.CYAN}●{S.RST} " if session.web_enabled else ""
            user_input = input(f"{web_dot}{S.BOLD}{S.BLUE}>{S.RST} ").strip()

            if not user_input:
                continue

            # 多行输入: 以 \ 结尾时续行
            while user_input.endswith('\\'):
                user_input = user_input[:-1] + '\n'
                try:
                    continuation = input(f"  {S.DIM}…{S.RST} ")
                    user_input += continuation
                except (KeyboardInterrupt, EOFError):
                    break

            # 命令处理
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()

                if command in ["/quit", "/exit", "/q"]:
                    print(f"\n  {S.DIM}再见 👋{S.RST}\n")
                    break
                elif command == "/help":
                    print_help()
                elif command == "/clear":
                    session.clear_history()
                elif command == "/web":
                    session.toggle_web()
                elif command == "/search":
                    if len(parts) > 1:
                        context = session.search_web(parts[1])
                        print(f"\n{S.DIM}{context}{S.RST}")
                    else:
                        print(f"  {S.DIM}用法: /search <搜索内容>{S.RST}")
                elif command == "/fetch":
                    if len(parts) > 1:
                        content = session.fetch_url(parts[1])
                        print(f"\n  {S.BOLD}网页内容:{S.RST}")
                        text = content[:2000] + '…' if len(content) > 2000 else content
                        print(text)
                    else:
                        print(f"  {S.DIM}用法: /fetch <URL>{S.RST}")
                elif command == "/models":
                    session.list_models()
                elif command == "/model":
                    if len(parts) > 1:
                        session.set_model(parts[1])
                    else:
                        print(f"  当前模型: {S.BOLD}{session.model}{S.RST}")
                        print(f"  {S.DIM}用法: /model <model_name>{S.RST}")
                elif command == "/history":
                    if len(session.messages) <= 1:
                        print(f"  {S.DIM}暂无对话历史{S.RST}")
                    else:
                        print()
                        for msg in session.messages:
                            role = msg["role"]
                            content = msg["content"]
                            if role == "system":
                                continue
                            if role == "user":
                                label = f"{S.BOLD}{S.BLUE}You{S.RST}"
                            else:
                                label = f"{S.BOLD}{S.GREEN}AI{S.RST}"
                            preview = content[:60].replace('\n', ' ')
                            if len(content) > 60:
                                preview += '…'
                            print(f"  {label}  {S.DIM}{preview}{S.RST}")
                        print()
                else:
                    print(f"  {S.RED}未知命令: {command}{S.RST}")
                    print(f"  {S.DIM}输入 /help 查看可用命令{S.RST}")
                continue

            # 发送消息
            print()
            session.chat(user_input)
            print()

        except KeyboardInterrupt:
            print(f"\n  {S.DIM}Ctrl+C — 输入 /quit 退出{S.RST}")
        except EOFError:
            print(f"\n  {S.DIM}再见 👋{S.RST}\n")
            break


# ── 入口 ──────────────────────────────────────────────────────────────

def main():
    config = ConfigManager()

    # 子命令预检: config / models
    if len(sys.argv) >= 2:
        subcmd = sys.argv[1]

        if subcmd == "config":
            handle_config(config, sys.argv[2:])
            return

        if subcmd == "models":
            handle_models(config, sys.argv[2:])
            return

    # 确保 API Key 存在
    if not config.ensure_api_key():
        sys.exit(1)

    session = ChatSession(config)

    # 单次查询模式: vchat "问题"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        session.toggle_web(True)
        session.chat(query, quiet=True)
        return

    # 交互式 REPL
    repl(session)

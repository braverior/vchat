import sys

from vchat.styles import S, get_terminal_width
from vchat.config import ConfigManager
from vchat.chat import ChatSession
from vchat.history import HistoryManager
from vchat.input import InputReader
from vchat.screen import Screen


# ── 帮助与界面 ───────────────────────────────────────────────────────────

def print_help():
    cmds = [
        ("/model <name>",  "切换模型"),
        ("/models",        "列出所有可用模型"),
        ("/web",           "切换联网模式 (或 Shift+Tab)"),
        ("/search <query>","手动搜索 (不发送给AI)"),
        ("/fetch <url>",   "获取指定网页内容"),
        ("/clear",         "清空对话历史"),
        ("/history",       "显示当前对话历史"),
        ("/convs",         "列出本地保存的对话"),
        ("/load <编号>",    "加载历史对话"),
        ("/new",           "开始新对话"),
        ("/delete <编号>",  "删除历史对话"),
        ("/help",          "显示此帮助信息"),
        ("/quit",          "退出程序"),
    ]
    print()
    print(f"  {S.BOLD}命令列表{S.RST}")
    print(f"  {S.DIM}{'─' * 44}{S.RST}")
    for cmd, desc in cmds:
        print(f"  {S.CYAN}{cmd:<20}{S.RST} {S.DIM}{desc}{S.RST}")
    print()
    print(f"  {S.DIM}提示: Shift+Tab 快速切换联网模式{S.RST}")
    print()


def print_banner(session):
    w = min(get_terminal_width(), 56)
    print()
    print(f"  {S.BOLD}{S.CYAN}vchat{S.RST}{S.DIM} — AI Chat{S.RST}")
    print(f"  {S.DIM}{'─' * (w - 4)}{S.RST}")
    print(f"  {S.DIM}/help 查看命令 · Shift+Tab 切换联网{S.RST}")
    print()


# ── 子命令处理 ────────────────────────────────────────────────────────

def handle_config(config, args):
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
    session = ChatSession(config)
    if args and args[0] == "set" and len(args) >= 2:
        session.set_model(args[1], persist=True)
        return
    if args and args[0] == "set":
        print(f"  {S.DIM}用法: vchat models set <model_name>{S.RST}")
        return
    session.list_models()


# ── 历史对话操作 ──────────────────────────────────────────────────────

def show_conversations(history):
    convs = history.list_conversations()
    if not convs:
        print(f"\n  {S.DIM}暂无保存的历史对话{S.RST}\n")
        return
    print()
    print(f"  {S.BOLD}历史对话{S.RST}")
    print(f"  {S.DIM}{'─' * 52}{S.RST}")
    for i, c in enumerate(convs, 1):
        ts = c["updated_at"][:10] if c["updated_at"] else ""
        ts_short = ts[5:] if ts else ""
        title = c["title"][:24]
        if len(c["title"]) > 24:
            title += "…"
        count = c["msg_count"]
        current = " ◄" if c["id"] == history.current_id else ""
        print(
            f"  {S.CYAN}{i:>3}{S.RST}  "
            f"{S.DIM}{ts_short}{S.RST}  "
            f"{title:<26}"
            f"{S.DIM}{count}条{S.RST}"
            f"{S.GREEN}{current}{S.RST}"
        )
    print(f"  {S.DIM}{'─' * 52}{S.RST}")
    print(f"  {S.DIM}用法: /load <编号> 加载 · /delete <编号> 删除{S.RST}")
    print()


def load_conversation(session, history, screen, num_str):
    convs = history.list_conversations()
    try:
        idx = int(num_str) - 1
    except ValueError:
        print(f"  {S.RED}请输入有效编号{S.RST}")
        return False
    if idx < 0 or idx >= len(convs):
        print(f"  {S.RED}编号超出范围 (1-{len(convs)}){S.RST}")
        return False
    conv = convs[idx]
    result = history.load(conv["id"])
    if not result:
        print(f"  {S.RED}加载失败{S.RST}")
        return False
    messages, model, web_enabled = result
    session.messages = messages
    if model:
        session.model = model
        screen.model = model
    session.web_enabled = web_enabled
    screen.web_enabled = web_enabled
    session.messages[0] = {"role": "system", "content": session._get_system_prompt()}
    screen.update_status()
    msg_count = len([m for m in messages if m["role"] != "system"])
    print(f"  {S.GREEN}已加载: {conv['title']}{S.RST}  {S.DIM}({msg_count}条消息){S.RST}")
    return True


def delete_conversation(history, num_str):
    convs = history.list_conversations()
    try:
        idx = int(num_str) - 1
    except ValueError:
        print(f"  {S.RED}请输入有效编号{S.RST}")
        return
    if idx < 0 or idx >= len(convs):
        print(f"  {S.RED}编号超出范围 (1-{len(convs)}){S.RST}")
        return
    conv = convs[idx]
    if history.delete(conv["id"]):
        print(f"  {S.DIM}已删除: {conv['title']}{S.RST}")
    else:
        print(f"  {S.RED}删除失败{S.RST}")


def start_new_conversation(session, history):
    user_msgs = [m for m in session.messages if m["role"] == "user"]
    if user_msgs:
        history.save(session.messages, session.model, session.web_enabled)
    history.new_conversation()
    session.clear_history()
    print(f"  {S.CYAN}已开始新对话{S.RST}")


# ── REPL 循环 ─────────────────────────────────────────────────────────

def repl(session):
    reader = InputReader()
    history = HistoryManager()
    history.new_conversation()

    screen = Screen()
    screen.setup(session.model, session.web_enabled)

    # Banner 输出在滚动区
    print_banner(session)

    def on_shift_tab():
        session.web_enabled = not session.web_enabled
        session.messages[0] = {"role": "system", "content": session._get_system_prompt()}
        screen.web_enabled = session.web_enabled

    try:
        while True:
            try:
                user_input = reader.read(screen, on_shift_tab).strip()
                # 回到滚动区，确保后续输出在输入框上方
                screen.to_scroll()

                if not user_input:
                    continue

                # ── 命令 ──
                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    command = parts[0].lower()

                    if command in ["/quit", "/exit", "/q"]:
                        user_msgs = [m for m in session.messages if m["role"] == "user"]
                        if user_msgs:
                            history.save(session.messages, session.model, session.web_enabled)
                        print(f"\n  {S.DIM}再见 👋{S.RST}\n")
                        break
                    elif command == "/help":
                        print_help()
                    elif command == "/clear":
                        user_msgs = [m for m in session.messages if m["role"] == "user"]
                        if user_msgs:
                            history.save(session.messages, session.model, session.web_enabled)
                            history.new_conversation()
                        session.clear_history()
                    elif command == "/web":
                        session.toggle_web()
                        screen.web_enabled = session.web_enabled
                        screen.update_status()
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
                            screen.model = session.model
                            screen.update_status()
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
                    elif command in ["/convs", "/conversations"]:
                        show_conversations(history)
                    elif command == "/load":
                        if len(parts) > 1:
                            user_msgs = [m for m in session.messages if m["role"] == "user"]
                            if user_msgs:
                                history.save(session.messages, session.model, session.web_enabled)
                            load_conversation(session, history, screen, parts[1].strip())
                        else:
                            print(f"  {S.DIM}用法: /load <编号>  (先用 /convs 查看列表){S.RST}")
                    elif command == "/new":
                        start_new_conversation(session, history)
                    elif command == "/delete":
                        if len(parts) > 1:
                            delete_conversation(history, parts[1].strip())
                        else:
                            print(f"  {S.DIM}用法: /delete <编号>  (先用 /convs 查看列表){S.RST}")
                    else:
                        print(f"  {S.RED}未知命令: {command}{S.RST}")
                        print(f"  {S.DIM}输入 /help 查看可用命令{S.RST}")
                    continue

                # ── 发送消息 ──
                print()
                session.chat(user_input)
                print()

                # 自动保存
                history.save(session.messages, session.model, session.web_enabled)

            except KeyboardInterrupt:
                screen.to_scroll()
                print(f"\n  {S.DIM}Ctrl+C — 输入 /quit 退出{S.RST}")

    except EOFError:
        screen.to_scroll()
        user_msgs = [m for m in session.messages if m["role"] == "user"]
        if user_msgs:
            history.save(session.messages, session.model, session.web_enabled)
        print(f"\n  {S.DIM}再见 👋{S.RST}\n")

    finally:
        screen.cleanup()


# ── 入口 ──────────────────────────────────────────────────────────────

def main():
    config = ConfigManager()

    if len(sys.argv) >= 2:
        subcmd = sys.argv[1]
        if subcmd == "config":
            handle_config(config, sys.argv[2:])
            return
        if subcmd == "models":
            handle_models(config, sys.argv[2:])
            return

    if not config.ensure_api_key():
        sys.exit(1)

    session = ChatSession(config)

    # 单次查询模式
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        session.toggle_web(True)
        session.chat(query, quiet=True)
        return

    repl(session)

import json
import os
import glob

from datetime import datetime

from vchat.defaults import CONFIG_DIR


HISTORY_DIR = os.path.join(os.path.expanduser(CONFIG_DIR), "history")


class HistoryManager:
    """管理本地对话历史，每个对话存储为独立 JSON 文件"""

    def __init__(self):
        self._dir = HISTORY_DIR
        os.makedirs(self._dir, exist_ok=True)
        self._current_id = None

    @property
    def current_id(self):
        return self._current_id

    def new_conversation(self):
        """创建新对话，返回 ID"""
        self._current_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._current_id

    def save(self, messages, model, web_enabled=False):
        """保存当前对话到文件"""
        if not self._current_id:
            self.new_conversation()

        # 至少需要有 system + 一条用户消息
        user_msgs = [m for m in messages if m["role"] == "user"]
        if not user_msgs:
            return

        title = self._make_title(user_msgs[0]["content"])
        now = datetime.now().isoformat(timespec="seconds")

        # 读取已有数据以保留 created_at
        path = self._path(self._current_id)
        created_at = now
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                created_at = old.get("created_at", now)
            except (json.JSONDecodeError, IOError):
                pass

        data = {
            "id": self._current_id,
            "title": title,
            "model": model,
            "created_at": created_at,
            "updated_at": now,
            "web_enabled": web_enabled,
            "messages": messages,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_conversations(self, limit=20):
        """列出最近的对话，按更新时间倒序"""
        files = glob.glob(os.path.join(self._dir, "*.json"))
        convs = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                convs.append({
                    "id": data["id"],
                    "title": data.get("title", "无标题"),
                    "model": data.get("model", ""),
                    "updated_at": data.get("updated_at", ""),
                    "msg_count": len([m for m in data.get("messages", []) if m["role"] != "system"]),
                })
            except (json.JSONDecodeError, IOError, KeyError):
                continue

        convs.sort(key=lambda c: c["updated_at"], reverse=True)
        return convs[:limit]

    def load(self, conv_id):
        """加载指定对话，返回 (messages, model, web_enabled) 或 None"""
        path = self._path(conv_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._current_id = data["id"]
            return (
                data["messages"],
                data.get("model", ""),
                data.get("web_enabled", False),
            )
        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def delete(self, conv_id):
        """删除指定对话"""
        path = self._path(conv_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def _path(self, conv_id):
        return os.path.join(self._dir, f"{conv_id}.json")

    @staticmethod
    def _make_title(first_message):
        """从第一条用户消息生成标题"""
        text = first_message.strip().split("\n")[0]
        if text.startswith("用户问题:"):
            text = text[len("用户问题:"):].strip()
        if len(text) > 30:
            text = text[:30] + "…"
        return text

import json
import os
import sys

from vchat.defaults import DEFAULT_BASE_URL, DEFAULT_MODEL, CONFIG_DIR, CONFIG_FILE
from vchat.styles import S


class ConfigManager:
    """管理 vchat 配置，优先级: 环境变量 > ~/.vchat/config.json > 默认值"""

    ENV_MAP = {
        "api_key":  ["AI_CHAT_API_KEY", "BLUEAI_API_KEY"],
        "base_url": ["AI_CHAT_BASE_URL"],
        "model":    ["AI_CHAT_MODEL"],
    }

    DEFAULTS = {
        "api_key":  "",
        "base_url": DEFAULT_BASE_URL,
        "model":    DEFAULT_MODEL,
    }

    VALID_KEYS = {"api_key", "base_url", "model"}

    def __init__(self):
        self._config_dir = os.path.expanduser(CONFIG_DIR)
        self._config_path = os.path.join(self._config_dir, CONFIG_FILE)
        self._file_data = self._load_file()

    # ── 属性 ──────────────────────────────────────────

    @property
    def api_key(self):
        return self._resolve("api_key")

    @property
    def base_url(self):
        return self._resolve("base_url")

    @property
    def model(self):
        return self._resolve("model")

    # ── 公开方法 ──────────────────────────────────────

    def set(self, key, value):
        """设置配置项并持久化到文件"""
        if key not in self.VALID_KEYS:
            print(f"  {S.RED}无效的配置项: {key}{S.RST}")
            print(f"  {S.DIM}可选: {', '.join(sorted(self.VALID_KEYS))}{S.RST}")
            return False
        self._file_data[key] = value
        self._save_file()
        print(f"  {S.CYAN}已保存 {key} 到 {self._config_path}{S.RST}")
        return True

    def show(self):
        """显示当前配置及来源"""
        print()
        print(f"  {S.BOLD}当前配置{S.RST}")
        print(f"  {S.DIM}{'─' * 44}{S.RST}")
        for key in ["api_key", "base_url", "model"]:
            value, source = self._resolve_with_source(key)
            display = self._mask(key, value)
            print(f"  {S.CYAN}{key:<12}{S.RST} {display}  {S.DIM}({source}){S.RST}")
        print(f"  {S.DIM}{'─' * 44}{S.RST}")
        print(f"  {S.DIM}配置文件: {self._config_path}{S.RST}")
        print()

    def ensure_api_key(self):
        """确保 API Key 已设置，未设置时交互式引导"""
        if self.api_key:
            return True
        print()
        print(f"  {S.BOLD}{S.YELLOW}首次使用设置{S.RST}")
        print(f"  {S.DIM}{'─' * 44}{S.RST}")
        print(f"  {S.DIM}未检测到 API Key，请进行初始配置。{S.RST}")
        print(f"  {S.DIM}你也可以设置环境变量 AI_CHAT_API_KEY 或 BLUEAI_API_KEY{S.RST}")
        print()
        try:
            key = input(f"  {S.BOLD}请输入 API Key: {S.RST}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {S.DIM}已取消{S.RST}")
            return False
        if not key:
            print(f"  {S.RED}API Key 不能为空{S.RST}")
            return False

        # 询问是否自定义 base_url
        print()
        try:
            custom_url = input(f"  {S.BOLD}Base URL{S.RST} {S.DIM}(回车使用默认 {DEFAULT_BASE_URL}){S.RST}: ").strip()
        except (KeyboardInterrupt, EOFError):
            custom_url = ""

        self._file_data["api_key"] = key
        if custom_url:
            self._file_data["base_url"] = custom_url
        self._save_file()

        print()
        print(f"  {S.GREEN}配置已保存到 {self._config_path}{S.RST}")
        print()
        return True

    # ── 内部方法 ──────────────────────────────────────

    def _resolve(self, key):
        """解析配置值: 环境变量 > 文件 > 默认"""
        value, _ = self._resolve_with_source(key)
        return value

    def _resolve_with_source(self, key):
        # 检查环境变量
        for env_name in self.ENV_MAP.get(key, []):
            val = os.environ.get(env_name)
            if val:
                return val, f"env:{env_name}"
        # 检查配置文件
        if key in self._file_data and self._file_data[key]:
            return self._file_data[key], "config file"
        # 返回默认值
        return self.DEFAULTS.get(key, ""), "default"

    def _load_file(self):
        """加载配置文件"""
        if not os.path.exists(self._config_path):
            return {}
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_file(self):
        """保存配置到文件"""
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(self._file_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _mask(key, value):
        """对敏感字段做掩码显示"""
        if key == "api_key" and value and len(value) > 8:
            return value[:4] + "****" + value[-4:]
        return value or "(未设置)"

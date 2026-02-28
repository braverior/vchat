import json
import time
import urllib.request
import urllib.error

from datetime import datetime

from vchat.styles import S
from vchat.render import StreamRenderer, Spinner
from vchat.search import WebSearch


class ChatSession:
    def __init__(self, config):
        """接收 ConfigManager 实例"""
        self.config = config
        self.model = config.model
        self.messages = []
        self.web_enabled = False
        self.messages.append({"role": "system", "content": self._get_system_prompt()})

    @property
    def api_key(self):
        return self.config.api_key

    @property
    def base_url(self):
        return self.config.base_url

    def _get_current_time_info(self):
        now = datetime.now()
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[now.weekday()]
        return (f"当前时间信息：\n"
                f"- 现在是：{now.strftime('%Y年%m月%d日 %H:%M:%S')} {weekday}\n"
                f"- 今天是：{now.strftime('%Y年%m月%d日')} {weekday}\n"
                f"- 今年是：{now.year}年\n"
                f"- 本月是：{now.year}年{now.month}月")

    def _get_system_prompt(self):
        time_info = self._get_current_time_info()
        if self.web_enabled:
            return (f"你是一个智能助手，具有联网搜索能力。当用户询问需要最新信息的问题时，你可以参考提供的搜索结果来回答。\n\n"
                    f"{time_info}\n\n"
                    f"请注意：\n1. 搜索结果会以特殊格式提供给你，请根据这些信息回答用户问题\n"
                    f"2. 如果搜索结果与问题相关，请综合这些信息给出准确的回答\n"
                    f"3. 如果搜索结果不够相关或信息不足，请诚实告知用户\n"
                    f"4. 回答时可以引用来源，但要用自然的语言组织答案\n"
                    f"5. 当用户提到\"今天\"、\"今年\"、\"现在\"等相对时间词时，请参考上面的时间信息来理解")
        else:
            return (f"你是一个智能助手，请用简洁清晰的语言回答用户的问题。\n\n"
                    f"{time_info}\n\n"
                    f"当用户提到\"今天\"、\"今年\"、\"现在\"等相对时间词时，请参考上面的时间信息来理解。")

    def toggle_web(self, enable=None):
        if enable is None:
            self.web_enabled = not self.web_enabled
        else:
            self.web_enabled = enable
        self.messages[0] = {"role": "system", "content": self._get_system_prompt()}
        status = f"{S.CYAN}● 联网模式已开启{S.RST}" if self.web_enabled else f"{S.DIM}○ 联网模式已关闭{S.RST}"
        print(f"  {status}")

    def set_model(self, model_name, persist=False):
        self.model = model_name
        if persist:
            self.config.set("model", model_name)
        else:
            print(f"  {S.CYAN}已切换模型为: {S.BOLD}{self.model}{S.RST}")

    def clear_history(self):
        self.messages = [{"role": "system", "content": self._get_system_prompt()}]
        print(f"  {S.DIM}对话历史已清空{S.RST}")

    def list_models(self):
        if not self.api_key:
            print(f"  {S.RED}错误: API Key 未设置{S.RST}")
            return
        url = f"{self.base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                if "data" in data:
                    print(f"\n  {S.BOLD}可用模型列表:{S.RST}")
                    for model in data["data"]:
                        marker = f"{S.CYAN}●{S.RST}" if model['id'] == self.model else f"{S.DIM}○{S.RST}"
                        print(f"    {marker} {model['id']}")
                    print()
                else:
                    print(f"  {S.DIM}未找到模型列表{S.RST}")
        except Exception as e:
            print(f"  {S.RED}获取模型列表失败: {e}{S.RST}")

    def search_web(self, query):
        print(f"  {S.DIM}{S.CYAN}🔍 搜索: {query}{S.RST}")
        results, context = WebSearch.search_and_summarize(query)
        if results:
            print(f"  {S.DIM}找到 {len(results)} 条结果{S.RST}")
            for i, r in enumerate(results, 1):
                title = r['title'][:48] + '…' if len(r['title']) > 48 else r['title']
                print(f"    {S.DIM}{i}. {title}{S.RST}")
        return context

    def fetch_url(self, url):
        print(f"  {S.DIM}{S.CYAN}📄 获取网页: {url}{S.RST}")
        return WebSearch.fetch_webpage(url)

    def chat(self, user_input, quiet=False):
        if not self.api_key:
            print(f"  {S.RED}错误: API Key 未设置。请运行 vchat config set api_key <your_key>{S.RST}")
            return

        # 联网搜索增强
        enhanced_input = user_input
        if self.web_enabled:
            search_keywords = ['最新', '今天', '现在', '目前', '新闻', '价格', '天气', '股票',
                             '搜索', '查询', '查一下', '帮我查', '是什么', '怎么样', '如何',
                             'latest', 'today', 'now', 'current', 'news', 'price', 'weather',
                             '2024', '2025', '2026']
            should_search = any(kw in user_input.lower() for kw in search_keywords)
            if should_search or len(user_input) > 10:
                search_context = self.search_web(user_input)
                if search_context:
                    enhanced_input = (f"用户问题: {user_input}\n\n"
                                      f"以下是从互联网搜索到的相关信息，请参考这些信息回答用户的问题：\n\n"
                                      f"{search_context}\n\n"
                                      f"请根据以上搜索结果，用简洁清晰的语言回答用户的问题。如果搜索结果不够相关，可以结合你的知识来回答。")

        self.messages.append({"role": "user", "content": enhanced_input})

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": self.messages,
            "temperature": 0.7,
            "stream": True
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        assistant_response = ""
        start_time = time.time()
        spinner = Spinner("思考中")

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers
            )

            spinner.start()

            first_token = True
            renderer = StreamRenderer()

            with urllib.request.urlopen(req) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    if first_token:
                                        spinner.stop()
                                        first_token = False
                                    content = delta["content"]
                                    renderer.feed(content)
                                    assistant_response += content
                        except json.JSONDecodeError:
                            continue

            if first_token:
                spinner.stop()

            renderer.flush()
            elapsed = time.time() - start_time

            if not quiet:
                chars = len(assistant_response)
                print(f"  {S.DIM}{'─' * 40}{S.RST}")
                print(f"  {S.DIM}{self.model}  ·  {chars} 字  ·  {elapsed:.1f}s{S.RST}")

            self.messages[-1] = {"role": "user", "content": user_input}
            self.messages.append({"role": "assistant", "content": assistant_response})

        except urllib.error.HTTPError as e:
            spinner.stop()
            print(f"\n  {S.RED}{S.BOLD}HTTP 错误 {e.code}{S.RST}{S.RED} — {e.reason}{S.RST}")
            try:
                body = e.read().decode('utf-8')
                if body:
                    print(f"  {S.DIM}{S.RED}{body[:200]}{S.RST}")
            except Exception:
                pass
            self.messages.pop()
        except urllib.error.URLError as e:
            spinner.stop()
            print(f"\n  {S.RED}网络错误: {e.reason}{S.RST}")
            self.messages.pop()
        except KeyboardInterrupt:
            spinner.stop()
            print(f"\n  {S.DIM}(已中断){S.RST}")
            if assistant_response:
                self.messages[-1] = {"role": "user", "content": user_input}
                self.messages.append({"role": "assistant", "content": assistant_response})
            else:
                self.messages.pop()
        except Exception as e:
            spinner.stop()
            print(f"\n  {S.RED}错误: {e}{S.RST}")
            self.messages.pop()

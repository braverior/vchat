import json
import re
import urllib.request
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser

from vchat.styles import S


class HTMLTextExtractor(HTMLParser):
    """从HTML中提取纯文本"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'nav', 'footer', 'header', 'aside'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text.append(text)

    def get_text(self):
        return ' '.join(self.text)


class WebSearch:
    """网络搜索功能"""

    @staticmethod
    def search_baidu(query, num_results=5):
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.baidu.com/s?wd={encoded_query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cookie": "BAIDUID=random123"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', errors='ignore')

            results = []
            title_pattern = r'<h3[^>]*><a[^>]*href="([^"]*)"[^>]*(?:data-showurl="([^"]*)")?[^>]*>(.*?)</a></h3>'
            matches = re.findall(title_pattern, html, re.DOTALL)
            for match in matches[:num_results]:
                link = match[0]
                real_url = match[1] if match[1] else link
                title = re.sub(r'<[^>]+>', '', match[2]).strip()
                if title and link:
                    results.append({
                        "title": title,
                        "url": real_url if real_url.startswith('http') else link,
                        "snippet": ""
                    })

            if not results:
                alt_pattern = r'<a[^>]*class="[^"]*c-showurl[^"]*"[^>]*>([^<]*)</a>'
                urls = re.findall(alt_pattern, html)
                title_pattern2 = r'<a[^>]*data-click[^>]*>(.*?)</a>'
                titles = re.findall(title_pattern2, html, re.DOTALL)
                for i, title in enumerate(titles[:num_results]):
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    if clean_title and len(clean_title) > 5:
                        results.append({
                            "title": clean_title,
                            "url": urls[i] if i < len(urls) else "",
                            "snippet": ""
                        })
            return results
        except Exception as e:
            print(f"  {S.DIM}{S.YELLOW}百度搜索出错: {e}{S.RST}")
            return []

    @staticmethod
    def search_bing(query, num_results=5):
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://cn.bing.com/search?q={encoded_query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', errors='ignore')

            results = []
            result_blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL)
            for block in result_blocks[:num_results]:
                title_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>', block)
                snippet_match = re.search(r'<p[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</p>', block)
                if title_match:
                    link = title_match.group(1)
                    title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
                    snippet = ""
                    if snippet_match:
                        snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                    if link.startswith('http'):
                        results.append({"title": title, "url": link, "snippet": snippet})
            return results
        except Exception as e:
            print(f"  {S.DIM}{S.YELLOW}Bing搜索出错: {e}{S.RST}")
            return []

    @staticmethod
    def search_duckduckgo_api(query, num_results=5):
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            results = []
            if data.get('Abstract'):
                results.append({
                    "title": data.get('Heading', query),
                    "url": data.get('AbstractURL', ''),
                    "snippet": data.get('Abstract', '')
                })
            for topic in data.get('RelatedTopics', [])[:num_results - len(results)]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        "title": topic.get('Text', '')[:50],
                        "url": topic.get('FirstURL', ''),
                        "snippet": topic.get('Text', '')
                    })
            return results
        except Exception as e:
            print(f"  {S.DIM}{S.YELLOW}DuckDuckGo API出错: {e}{S.RST}")
            return []

    @staticmethod
    def search(query, num_results=5):
        results = WebSearch.search_baidu(query, num_results)
        if results:
            return results
        print(f"  {S.DIM}尝试 Bing 搜索...{S.RST}")
        results = WebSearch.search_bing(query, num_results)
        if results:
            return results
        print(f"  {S.DIM}尝试 DuckDuckGo...{S.RST}")
        return WebSearch.search_duckduckgo_api(query, num_results)

    @staticmethod
    def fetch_webpage(url, max_length=4000):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            extractor = HTMLTextExtractor()
            extractor.feed(html)
            text = extractor.get_text()
            if len(text) > max_length:
                text = text[:max_length] + "..."
            return text
        except Exception as e:
            return f"无法获取网页内容: {e}"

    @staticmethod
    def search_and_summarize(query, num_results=3, fetch_content=True):
        results = WebSearch.search(query, num_results)
        if not results:
            return None, "未找到相关搜索结果"

        search_context = f"搜索查询: {query}\n"
        search_context += f"搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n搜索结果:\n"

        for i, result in enumerate(results, 1):
            search_context += f"\n{i}. {result['title']}\n   URL: {result['url']}\n   摘要: {result['snippet']}\n"
            if fetch_content and result['url'] and result['url'].startswith('http'):
                try:
                    print(f"  {S.DIM}{S.CYAN}  获取第 {i} 条网页...{S.RST}")
                    page_content = WebSearch.fetch_webpage(result['url'], max_length=2000)
                    if page_content and not page_content.startswith("无法获取"):
                        search_context += f"   网页内容: {page_content}\n"
                        result['content'] = page_content
                    else:
                        search_context += f"   网页内容: (无法获取)\n"
                except Exception as e:
                    search_context += f"   网页内容: (获取失败: {e})\n"

        return results, search_context

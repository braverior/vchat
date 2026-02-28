# vchat

终端 AI 聊天工具。零依赖，流式 Markdown 渲染，支持联网搜索。

## 安装

```bash
pip install -e .
```

安装后即可使用 `vchat` 命令。

## 快速开始

首次运行会引导你设置 API Key：

```bash
vchat
```

也可以手动配置：

```bash
vchat config set api_key sk-your-key-here
```

## 使用

### 交互模式

```bash
vchat
```

进入 REPL，支持多轮对话、联网搜索、模型切换等。

### 单次查询

```bash
vchat "TCP 和 UDP 的区别"
```

自动开启联网模式，输出后退出。

### 配置管理

```bash
vchat config                          # 查看当前配置及来源
vchat config set api_key sk-xxx       # 设置 API Key
vchat config set base_url https://... # 设置 API 地址
vchat config set model gpt-4          # 设置默认模型
```

配置文件保存在 `~/.vchat/config.json`。

### 模型管理

```bash
vchat models                # 列出可用模型
vchat models set gpt-4      # 设置默认模型并持久化
```

## 交互命令

| 命令 | 说明 |
|------|------|
| `/model <name>` | 切换模型（当前会话） |
| `/models` | 列出可用模型 |
| `/web` | 切换联网模式 |
| `/search <query>` | 手动搜索（不发送给 AI） |
| `/fetch <url>` | 获取网页内容 |
| `/clear` | 清空对话历史 |
| `/history` | 显示对话历史 |
| `/help` | 帮助 |
| `/quit` | 退出 |

行末输入 `\` 可续行输入多行文本。

## 配置优先级

环境变量 > `~/.vchat/config.json` > 默认值

支持的环境变量：

| 环境变量 | 说明 |
|----------|------|
| `AI_CHAT_API_KEY` | API Key |
| `BLUEAI_API_KEY` | API Key（备选） |
| `AI_CHAT_BASE_URL` | API 地址 |
| `AI_CHAT_MODEL` | 默认模型 |

## 项目结构

```
vchat/
  __init__.py    # 版本号
  __main__.py    # python -m vchat
  defaults.py    # 默认常量
  styles.py      # ANSI 样式
  render.py      # 流式 Markdown 渲染 + 思考动画
  search.py      # 网络搜索（百度/Bing/DuckDuckGo）
  config.py      # 配置管理
  chat.py        # 聊天会话
  cli.py         # CLI 入口 + REPL
```

## 要求

- Python >= 3.8
- 零外部依赖

# Gameing4Free 自动续期脚本

这个项目是一个使用 Python 编写的自动续期脚本，旨在为 `https://gaming4free.net/servers/my-game` 游戏服务器提供自动续期服务。

## 功能特性

1. **自动状态检查**：自动读取服务器当前的剩余时间。
2. **智能续期控制**：如果剩余时间小于 2 小时，自动触发续期，否则自动跳过。
3. **Cloudflare 验证码绕过**：使用 `SeleniumBase` 提供的 Undetected ChromeDriver (UC) 模式来绕过并自动处理 Cloudflare Turnstile 验证码。
4. **即时 Telegram 通知**：无论是执行了续期还是跳过，都会向指定的 Telegram 机器人发送当前的续期状态报告。

## 安装与配置

### 1. 准备工作
请确保您的系统中已安装：
- **Python** (建议版本 >= 3.13)
- **uv** (推荐的 Python 虚拟环境与依赖包管理器)

### 2. 依赖安装
该项目已通过 `pyproject.toml` 声明依赖。当您使用 `uv run` 运行时，`uv` 会自动为您下载并管理 `seleniumbase` 及其相关驱动程序，无需手动执行繁琐的安装命令。

### 3. 配置 Telegram 环境变量
1. 复制项目根目录下的 `.env.example` 并重命名为 `.env`。
2. 编辑 `.env` 文件，填入您的 Telegram 机器人 Token 以及聊天 ID：
   ```ini
   TELEGRAM_BOT_TOKEN=你的_Telegram_机器人_Token
   TELEGRAM_CHAT_ID=接收通知的_Telegram_Chat_ID
   ```

## 使用方法

### 有头模式 (GUI 模式)
在本地运行调试时，此模式会显示浏览器界面，方便观察自动化交互流程与 Cloudflare 验证状态：
```powershell
uv run python main.py
```

### 无头模式 (Headless 模式)
在无界面服务器、定时任务（例如 Linux Cron、Windows 计划任务或 GitHub Actions）中部署时，请在命令末尾添加 `--headless` 参数以隐藏浏览器界面：
```powershell
uv run python main.py --headless
```

## 通知消息格式

脚本运行结束后会发送如下格式的通知：
- **需要续期的情况**：
  ```text
  Gameing4Free 自动续期：
      续期前时间：01:30:15
      续期后时间：04:00:00
      续期执行时间：2026-07-06 11:35:00
  ```
- **无需续期的情况**：
  ```text
  Gameing4Free 自动续期：
      续期前时间：03:45:00
      续期后时间：无需续期（大于等于2小时）
      续期执行时间：2026-07-06 11:35:00
  ```

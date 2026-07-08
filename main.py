import os
import sys
import time
import datetime
import urllib.request
import urllib.parse
from seleniumbase import SB


def load_env():
    """手动解析当前目录下的 .env 文件，避免引入外部依赖"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print(f"正在从 {env_path} 加载环境变量...")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
    else:
        print("未检测到本地 .env 文件，将使用系统环境变量。")


def send_telegram_notification(message):
    """发送 Telegram 通知"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(
            "【错误】未配置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，跳过 Telegram 发送。"
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
            print("【成功】Telegram 通知已发送。")
            return True
    except Exception as e:
        print(f"【错误】发送 Telegram 通知失败: {e}")
        return False


def send_telegram_photo(photo_path, caption=None):
    """发送 Telegram 图片"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(
            "【错误】未配置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，跳过 Telegram 图片发送。"
        )
        return False

    if not os.path.exists(photo_path):
        print(f"【错误】图片文件不存在: {photo_path}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = []

    # chat_id
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="chat_id"'.encode("utf-8"))
    body.append(b"")
    body.append(str(chat_id).encode("utf-8"))

    # caption
    if caption:
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(f'Content-Disposition: form-data; name="caption"'.encode("utf-8"))
        body.append(b"")
        body.append(caption.encode("utf-8"))

    # photo
    filename = os.path.basename(photo_path)
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(
        f'Content-Disposition: form-data; name="photo"; filename="{filename}"'.encode(
            "utf-8"
        )
    )
    body.append(b"Content-Type: image/png")
    body.append(b"")
    with open(photo_path, "rb") as f:
        body.append(f.read())

    body.append(f"--{boundary}--".encode("utf-8"))
    body.append(b"")

    payload = b"\r\n".join(body)

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(payload)))

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            response.read()
            print("【成功】Telegram 图片通知已发送。")
            return True
    except Exception as e:
        print(f"【错误】发送 Telegram 图片通知失败: {e}")
        return False


def parse_time_to_seconds(time_str):
    """将 HH:MM:SS 格式的时间转换为秒数"""
    time_str = time_str.strip()
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = map(int, parts)
        return h * 3600 + m * 60 + s
    raise ValueError(f"无法解析的时间格式: {time_str}")


def handle_consent_popup(sb):
    """检查并关闭隐私同意弹窗 (Google Funding Choices)"""
    selectors = [
        "button.fc-cta-consent",
        "div.fc-consent-root button.fc-primary-button",
        "//button[contains(@class, 'fc-cta-consent')]",
        "//p[text()='Consent' or text()='同意']/ancestor::button"
    ]
    for selector in selectors:
        try:
            if sb.is_element_present(selector):
                print(f"检测到隐私同意弹窗，尝试通过选择器 '{selector}' 点击同意...")
                sb.click(selector)
                sb.sleep(1.5)
                if not sb.is_element_present(selector):
                    print("隐私同意弹窗已成功关闭。")
                    return True
        except Exception as e:
            print(f"尝试使用选择器 '{selector}' 点击同意时出错: {e}")
    return False


def main():
    load_env()
    WARP_PROXY = os.environ.get("WARP_PROXY", "")

    # 使用 SeleniumBase UC (Undetected) 模式
    sb_options = {
        "uc": True,
        "test": True,
        "headed": True,
        "chromium_arg": "--window-size=1280,720",
    }
    # 如果是 Linux 系统且没有检测到外部提供 DISPLAY 环境变量，则开启 SeleniumBase 内置的 xvfb 虚拟显示器支持
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        sb_options["xvfb"] = True
    if WARP_PROXY:
        sb_options["proxy"] = WARP_PROXY
    with SB(**sb_options) as sb:
        url = "https://gaming4free.net/servers/my-game"
        print(f"正在打开网页: {url}")
        # uc_open_with_reconnect 在遭遇初始质询时会有更好的重连与保活表现
        sb.uc_open_with_reconnect(url, reconnect_time=4)

        # 检查并处理打开页面后的隐私同意弹框
        handle_consent_popup(sb)

        # 获取 div#sd-timer 的文本内容
        print("正在等待获取 div#sd-timer ...")
        sb.wait_for_element("div#sd-timer", timeout=15)
        before_time_text = sb.get_text("div#sd-timer").strip()
        print(f"续期前时间: {before_time_text}")

        # 点击按钮 button#sd-vote-btn
        print("点击续期按钮 button#sd-vote-btn")
        sb.uc_click("button#sd-vote-btn")

        # 检查并处理点击续期按钮后的隐私同意弹框
        handle_consent_popup(sb)

        # 等待弹出框中的 div#ts-widget 加载
        print("等待验证码区域 div#ts-widget 出现...")
        sb.wait_for_element("div#ts-widget", timeout=15)

        # 进行 Cloudflare Turnstile 验证码处理
        print("尝试解决 Cloudflare Turnstile 验证...")
        sb.sleep(5)  # 给验证码小部件一点渲染和稳定时间

        timeout_second = 120
        st = time.time()
        # 初始化 last_click 为当前时间，以便循环刚开始的 initial_wait 秒内给 Cloudflare 预留自动验证时间
        last_click = time.time()
        success = False
        
        initial_wait = 15  # 刚进入时先等待 15 秒让其尝试自动通过
        click_interval = 20  # 之后每隔 20 秒点击一次，防止高频重复点击被 CF 识别为恶意交互
        
        while time.time() - st < timeout_second:
            try:
                token_val = sb.execute_script(
                    "return (document.querySelector(\"[name='cf-turnstile-response']\") || {}).value;"
                )
                if token_val and len(token_val.strip()) > 0:
                    print(f"验证成功！已生成 Response Token: {token_val[:35]}...")
                    success = True
                    break
            except Exception:
                pass

            elapsed = time.time() - st
            if elapsed > initial_wait:
                if time.time() - last_click > click_interval:
                    print("未检测到有效 Token，尝试模拟键盘或鼠标交互触发验证...")
                    try:
                        # 优先使用专门针对 Cloudflare 的键盘聚焦模拟方法（TAB + SPACEBAR）
                        # 这种方法不依赖绝对物理坐标，能有效免疫由于广告加载引起的页面抖动和点偏问题
                        sb.uc_gui_handle_cf()
                        last_click = time.time()
                        print("已执行 uc_gui_handle_cf 键盘模拟。")
                    except Exception as e:
                        print(f"使用 uc_gui_handle_cf 失败: {e}，尝试使用常规鼠标点击...")
                        try:
                            sb.uc_gui_click_captcha()
                            last_click = time.time()
                            print("已执行 uc_gui_click_captcha 鼠标点击。")
                        except Exception as ex:
                            print(f"模拟点击失败: {ex}")

            # 点击或检测后稍微等待
            sb.sleep(2)

        if not success:
            print("【错误】未能在规定时间内生成验证码 Token，请尝试手动处理。")
            screenshot_path = "captcha_timeout.png"
            caption_msg = "Gameing4Free 自动续期：\n【错误】未能在规定时间内生成验证码 Token，请尝试手动处理。"
            try:
                print("正在截取当前页面截图...")
                sb.save_screenshot(screenshot_path)
                print(f"截图已保存到 {screenshot_path}，正在发送到 Telegram...")
                sent = send_telegram_photo(screenshot_path, caption=caption_msg)
                if not sent:
                    print("发送 Telegram 截图失败，降级发送普通文本通知...")
                    send_telegram_notification(caption_msg)
            except Exception as e:
                print(f"【错误】截图或发送截图失败: {e}，将降级发送普通文本通知。")
                send_telegram_notification(caption_msg)
            finally:
                if os.path.exists(screenshot_path):
                    try:
                        os.remove(screenshot_path)
                        print("临时截图文件已清理。")
                    except Exception as ce:
                        print(f"清理临时截图文件失败: {ce}")
            return

        print("【成功】检测到验证码已通过，准备提交。")

        # 点击提交按钮 button#vm-submit
        print("点击提交按钮 button#vm-submit")
        sb.click("button#vm-submit")

        # 取消固定的 5 秒等待，通过轮询与刷新等待有效的时间格式出现
        print("正在等待续期生效并获取新时间...")
        after_time_text = "—"
        success_update = False

        for check_attempt in range(10):
            sb.sleep(1.5)  # 每次循环稍微间隔
            try:
                sb.refresh()
                sb.wait_for_element("div#sd-timer", timeout=8)
                sb.sleep(5)
                current_time = sb.get_text("div#sd-timer").strip()
                if ":" in current_time and current_time != "—":
                    after_time_text = current_time
                    success_update = True
                    break
                else:
                    print(
                        f"【第 {check_attempt + 1}/10 次尝试】获取到的时间值为 '{current_time}'，尚未完成加载，继续刷新中..."
                    )
            except Exception as e:
                print(f"刷新或获取时间出错: {e}")

        if not success_update:
            print("【警告】未能成功在规定时间内获取到有效的续期后时间格式。")

        print(f"续期后时间: {after_time_text}")

        # 发送 Telegram 成功通知
        msg = f"""Gameing4Free 自动续期：
    续期前时间：{before_time_text}
    续期后时间：{after_time_text}"""
        send_telegram_notification(msg)


if __name__ == "__main__":
    main()

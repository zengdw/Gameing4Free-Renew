import os, platform, sys, time
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
        "//p[text()='Consent' or text()='同意']/ancestor::button",
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


def close_other_popups_and_ads(sb):
    """检查并清理/关闭页面上的其它广告、浮窗或非投票弹窗，以免遮挡验证码"""
    js_code = """
    (function() {
        const actions = [];
        // 1. 找到投票弹窗的原生容器（避免误删/误点其中的元素）
        const tsWidget = document.querySelector('#ts-widget');
        const voteSubmit = document.querySelector('button#vm-submit');
        let voteModal = null;
        if (tsWidget) {
            voteModal = tsWidget.closest('.modal, [class*="modal"], [class*="dialog"], [class*="popup"]');
            if (!voteModal) {
                voteModal = tsWidget.parentElement ? tsWidget.parentElement.parentElement : null;
            }
        } else if (voteSubmit) {
            voteModal = voteSubmit.closest('.modal, [class*="modal"], [class*="dialog"], [class*="popup"]');
        }

        // 2. 定义可能遮挡的广告/浮窗容器的选择器
        const adSelectors = [
            'iframe[id^="aswift"]', 
            'iframe[id^="google_ads"]', 
            'iframe[src*="doubleclick"]',
            'div[id^="google_ads"]',
            'ins.adsbygoogle',
            '#ad_position_box',
            '[class*="ad-overlay"]',
            '[class*="ad-container"]',
            '[class*="floating-ad"]',
            '[class*="video-ad"]',
            '[id*="google-vignette"]',
            '.google-vignette-focusable'
        ];

        adSelectors.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(el => {
                    if (voteModal && voteModal.contains(el)) return;
                    actions.push('隐藏/移除广告容器: ' + (el.id || el.className || el.tagName));
                    el.style.display = 'none';
                    el.remove();
                });
            } catch (e) {
                actions.push('处理选择器出错 (' + selector + '): ' + e.message);
            }
        });

        // 3. 定义广告/其它弹框关闭按钮的选择器
        const closeSelectors = [
            'button.close',
            'button[class*="close"]',
            'div[class*="close-btn"]',
            'div[class*="close-button"]',
            'div[class*="close-icon"]',
            'span[class*="close"]',
            'a[class*="close"]',
            '[aria-label*="close" i]',
            '[aria-label*="dismiss" i]',
            'svg[class*="close"]',
            '[id*="dismiss"]',
            '[class*="dismiss"]',
            '[id*="skip"]',
            '[class*="skip"]',
            '.primis-close-button'
        ];

        closeSelectors.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(el => {
                    if (voteModal && voteModal.contains(el)) return;
                    if (el.id === 'vm-close' || el.classList.contains('vm-close')) return;
                    
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        actions.push('点击关闭按钮: ' + (el.id || el.className || el.tagName));
                        el.click();
                    }
                });
            } catch (e) {
                actions.push('点击关闭按钮出错 (' + selector + '): ' + e.message);
            }
        });

        return actions;
    })();
    """
    try:
        actions = sb.execute_script(js_code)
        if actions:
            for action in actions:
                print(f"[清除广告/弹窗] {action}")
    except Exception as e:
        print(f"清理广告/弹窗时执行 JavaScript 出错: {e}")


def main():
    load_env()
    WARP_PROXY = os.environ.get("WARP_PROXY", "")

    # 使用 SeleniumBase UC (Undetected) 模式
    sb_options = {
        "uc": True,
        "xvfb": True,
        "incognito": True,
        "locale": "en",
    }
    if WARP_PROXY:
        sb_options["proxy"] = WARP_PROXY
    with SB(**sb_options) as sb:
        url = "https://gaming4free.net/servers/my-game"
        print(f"正在打开网页: {url}")
        # uc_open_with_reconnect 在遭遇初始质询时会有更好的重连与保活表现
        sb.activate_cdp_mode(url)

        # 检查并处理打开页面后的隐私同意弹框
        handle_consent_popup(sb)
        close_other_popups_and_ads(sb)

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
        close_other_popups_and_ads(sb)

        # 等待弹出框中的 div#ts-widget 加载
        print("等待验证码区域 div#ts-widget 出现...")
        sb.wait_for_element("div#ts-widget", timeout=15)

        timeout_second = 300
        st = time.time()
        success = False
        while time.time() - st < timeout_second:
            sb.sleep(15)
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

            print("未检测到有效 Token，尝试点击验证码 iframe 触发验证...")
            handle_consent_popup(sb)
            close_other_popups_and_ads(sb)
            try:
                sb.sleep(1)
                sb.uc_gui_click_captcha()
            except Exception as e:
                print(f"点击验证码失败: {e}")

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

# -*- coding: utf-8 -*-
"""库街区签到助手 — 独立版（不依赖 OKWW）
单文件 tkinter GUI：Token 签到 + 手机验证码登录（支持内嵌浏览器自动捕获 token）。
配置保存在 exe 同目录 kuro_config.json，日志 kuro_checkin_log.md。
命令行模式: KuroCheckin.exe --cli （无界面直接签到一次并打印结果）
"""
import json
import os
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import ttkbootstrap as ttkb
    ttk = ttkb  # 控件统一用 ttkbootstrap 版本，支持 bootstyle
except ImportError:
    ttkb = None

IS_FROZEN = getattr(sys, "frozen", False)
BASE_DIR = os.path.dirname(sys.executable) if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "kuro_config.json")
LOG_FILE = os.path.join(BASE_DIR, "kuro_checkin_log.md")

GAME_ID = "3"
WUWA_SERVER_ID = "76402e5b20be2c39f095a152090afddc"
WUWA_SERVER_ID_NET = "919752ae5ea09c1ced910dd668a63ffb"
IP = "10.0.2.233"
_URL_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) "
           "AppleWebKit/605.1.15 (KHTML, like Gecko)  KuroGameBox/3.1.3")
ANDROID_HEADERS = {
    "osversion": "Android", "countrycode": "CN", "ip": IP, "model": "2211133C",
    "source": "android", "lang": "zh-Hans", "version": "1.0.9", "versioncode": "1090",
    "content-type": "application/x-www-form-urlencoded", "accept-encoding": "gzip",
    "user-agent": "okhttp/3.10.0",
}
GAME_HEADERS = {
    "source": "ios", "version": "3.1.3", "User-Agent": _URL_UA,
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "devCode": f"{IP}, {_URL_UA}", "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9", "Connection": "keep-alive",
}
LOGIN_PAGE = "https://www.kurobbs.com/mc"


def _post(url, headers, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sdk_login(devcode, mobile, code):
    """验证码登录（验证码在库街区网页登录页获取）。返回 dict 或抛异常。"""
    h = dict(ANDROID_HEADERS)
    h["devcode"] = devcode
    h["distinct_id"] = devcode
    data = {"code": code, "devCode": devcode, "gameList": "", "mobile": mobile}
    r = _post("https://api.kurobbs.com/user/sdkLogin", h, data)
    if r.get("code") != 200 or not r.get("data"):
        raise RuntimeError(f"登录失败 code={r.get('code')} {r.get('msg')}")
    token = r["data"].get("token") or (r["data"].get("userInfo") or {}).get("token")
    if not token:
        raise RuntimeError(f"登录成功但未返回 token: {str(r)[:200]}")
    return token


def get_user_id(token, did):
    h = dict(ANDROID_HEADERS)
    h["devcode"] = did
    h["token"] = token
    r = _post("https://api.kurobbs.com/user/mineV2", h, {})
    if r.get("code") != 200 or not r.get("data"):
        raise RuntimeError(f"token 验证失败 code={r.get('code')} {r.get('msg')}")
    return int(r["data"]["mine"]["userId"])


def get_wuwa_role(token, did):
    h = dict(ANDROID_HEADERS)
    h["devcode"] = did
    h["token"] = token
    r = _post("https://api.kurobbs.com/user/role/findRoleList", h, {"gameId": GAME_ID})
    if r.get("code") != 200 or not r.get("data"):
        raise RuntimeError(f"获取角色失败 code={r.get('code')} {r.get('msg')}")
    if not r["data"]:
        raise RuntimeError("该账号未绑定鸣潮游戏角色")
    role = r["data"][0]
    role.setdefault("serverId", WUWA_SERVER_ID)
    return role


def do_sign_in(token, did, role):
    server_id = (WUWA_SERVER_ID_NET if int(role["roleId"]) >= 200000000
                 else (role.get("serverId") or WUWA_SERVER_ID))
    h = dict(GAME_HEADERS)
    h["token"] = token
    h["did"] = did
    h["b-at"] = ""
    h["devcode"] = ""
    try:
        r = _post("https://api.kurobbs.com/encourage/signIn/initSignInV2", h,
                  {"gameId": GAME_ID, "serverId": server_id, "roleId": str(role["roleId"])})
        if r.get("code") == 200 and isinstance(r.get("data"), dict) and r["data"].get("isSigIn"):
            return {"code": 1511, "msg": "今日已签到"}
    except Exception:
        pass
    data = {"gameId": GAME_ID, "serverId": server_id, "roleId": str(role["roleId"]),
            "reqMonth": datetime.now().strftime("%m")}
    return _post("https://api.kurobbs.com/encourage/signIn/v2", h, data)


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "KuroCheckin"


def get_autostart():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as k:
            winreg.QueryValueEx(k, APP_REG_NAME)
            return True
    except OSError:
        return False


def set_autostart(enable):
    import winreg
    if IS_FROZEN:
        target = f'"{sys.executable}" --minimized'
    else:
        target = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --minimized'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as k:
        if enable:
            winreg.SetValueEx(k, APP_REG_NAME, 0, winreg.REG_SZ, target)
        else:
            try:
                winreg.DeleteValue(k, APP_REG_NAME)
            except FileNotFoundError:
                pass


def _append_log(text):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"## {datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n")
    except Exception:
        pass


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def run_checkin(token, did):
    lines = []
    try:
        uid = get_user_id(token, did)
        lines.append(f"token/did 验证通过 userId={uid}")
        role = get_wuwa_role(token, did)
        role_name = role.get("roleName", "?")
        lines.append(f"角色 {role_name} roleId={role.get('roleId')}")
        r = do_sign_in(token, did, role)
        code, msg = r.get("code"), r.get("msg", "")
        if code == 200:
            _append_log("\n".join(lines) + "\n✅ 签到成功")
            return {"ok": True, "already": False, "state": "success",
                    "message": f"签到成功: {role_name}（请求成功）"}
        elif code == 1511:
            _append_log("\n".join(lines) + "\nℹ️ 今日已签到")
            return {"ok": True, "already": True, "state": "already",
                    "message": f"{role_name} 今日已签到过，无需重复签到"}
        elif code == 220:
            _append_log("\n".join(lines) + "\n❌ token 失效")
            return {"ok": False, "already": False, "state": "fail", "message": "token 已失效，请重新获取"}
        else:
            _append_log("\n".join(lines) + f"\n❌ 失败 code={code} {msg}")
            return {"ok": False, "already": False, "state": "fail",
                    "message": f"签到失败 code={code} {msg}"}
    except Exception as e:
        _append_log("\n".join(lines) + f"\n❌ 异常 {e}")
        return {"ok": False, "already": False, "state": "fail", "message": f"异常: {e}"}


def cli_mode():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cfg = load_config()
    token, did = (cfg.get("token") or "").strip(), (cfg.get("did") or "").strip()
    if not token or not did:
        print("未配置 token/did，请先运行图形界面填写: " + os.path.basename(sys.executable if IS_FROZEN else sys.argv[0]))
        sys.exit(1)
    r = run_checkin(token, did)
    print(("✅ " if r["ok"] else "❌ ") + r["message"])
    sys.exit(0 if r["ok"] else 1)


class App:
    def __init__(self, root):
        self.root = root
        self.tb = ttkb is not None
        root.geometry("640x490")
        root.minsize(560, 430)

        nb = ttk.Notebook(root, **self._o("primary"))
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_sign = ttk.Frame(nb, padding=14)
        self.tab_login = ttk.Frame(nb, padding=14)
        nb.add(self.tab_sign, text="  🏠 签到  ")
        nb.add(self.tab_login, text="  🔑 获取 Token  ")

        cfg = load_config()
        self._build_sign_tab(cfg)
        self._build_login_tab(cfg)
        self._wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def _o(self, style):
        """ttkbootstrap 主题参数（无 ttkbootstrap 时忽略）"""
        return {"bootstyle": style} if self.tb else {}

    def _build_sign_tab(self, cfg):
        f = self.tab_sign
        card = ttk.Labelframe(f, text=" 账号配置 ", padding=14, **self._o("primary"))
        card.pack(fill="x")
        ttk.Label(card, text="token").grid(row=0, column=0, sticky="w", pady=4)
        self.e_token = ttk.Entry(card, width=56)
        self.e_token.grid(row=0, column=1, sticky="we", pady=4, padx=(8, 0))
        self.e_token.insert(0, cfg.get("token", ""))
        ttk.Label(card, text="did").grid(row=1, column=0, sticky="w", pady=4)
        self.e_did = ttk.Entry(card, width=56)
        self.e_did.grid(row=1, column=1, sticky="we", pady=4, padx=(8, 0))
        self.e_did.insert(0, cfg.get("did", ""))
        card.columnconfigure(1, weight=1)

        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=10)
        ttk.Button(btns, text="💾 保存配置", command=self.save,
                   **self._o("secondary-outline")).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="⚡ 立即签到", command=self.manual,
                   **self._o("success")).pack(side="left", padx=(0, 8))
        ttk.Label(btns, text="每次打开本程序自动签到，跨天自动补签",
                  **self._o("secondary")).pack(side="left")

        opts = ttk.Frame(f)
        opts.pack(fill="x", pady=(0, 8))
        self.var_autostart = tk.BooleanVar(value=get_autostart())
        ttk.Checkbutton(opts, text="开机自动启动（登录 Windows 后自动运行并签到）",
                        variable=self.var_autostart, command=self.toggle_autostart,
                        **self._o("round-toggle")).pack(side="left")

        scard = ttk.Labelframe(f, text=" 签到状态 ", padding=10, **self._o("primary"))
        scard.pack(fill="both", expand=True)
        self.status = tk.Text(scard, height=7, wrap="word", state="disabled",
                              background="#f8f9fa", relief="flat",
                              font=("Microsoft YaHei UI", 10))
        self.status.pack(fill="both", expand=True)
        for tag, color in (("success", "#2fb344"), ("already", "#0099db"),
                           ("fail", "#e03131"), ("running", "#909296"), ("idle", "#5c5f66")):
            self.status.tag_configure(tag, font=("Microsoft YaHei UI", 10, "bold"),
                                      foreground=color)
        self._set_status("启动中…", "running")

    def _build_login_tab(self, cfg):
        f = self.tab_login
        card = ttk.Labelframe(f, text=" 获取 Token 的三种方式 ", padding=14,
                              **self._o("primary"))
        card.pack(fill="x")
        WL = 560  # 长文案自动换行宽度
        ttk.Label(card, text="① 内嵌浏览器登录（推荐，请用这个）", font=("Microsoft YaHei UI", 10, "bold"),
                  wraplength=WL).pack(anchor="w", pady=(0, 2))
        ttk.Label(card, text="程序内打开库街区页面并自动弹出登录窗口，"
                             "你只需划滑块 → 点获取验证码 → 填短信码 → 点登录，"
                             "点完窗口自动关闭、token/did 自动填入",
                  **self._o("secondary"), wraplength=WL).pack(anchor="w")
        ttk.Label(card, text="⚠ 登录就在程序弹出的这个窗口里完成；"
                             "不要自己另开 Chrome/Edge 等浏览器去登录，那样 token 抓不到",
                  foreground="#e03131", wraplength=WL).pack(anchor="w")
        ttk.Button(card, text="🚀 打开内嵌登录窗口", command=self.embedded_login,
                   **self._o("primary")).pack(fill="x", pady=(6, 10), ipady=2)

        ttk.Label(card, text="② 网页验证码登录（备用，仅在内嵌窗口打不开时用）", font=("Microsoft YaHei UI", 10, "bold"),
                  wraplength=WL).pack(anchor="w", pady=(4, 2))
        ttk.Label(card, text="仅在备用浏览器里点【获取验证码】收短信；不要在浏览器里登录，"
                             "回到程序里填手机号+短信码，由程序完成登录",
                  **self._o("secondary"), wraplength=WL).pack(anchor="w")
        login_card = ttk.Frame(card)
        login_card.pack(fill="x", pady=(6, 4))
        ttk.Label(login_card, text="手机号:").pack(side="left")
        self.e_mobile = ttk.Entry(login_card, width=18)
        self.e_mobile.pack(side="left", padx=(4, 12))
        self.e_mobile.insert(0, cfg.get("phone", ""))
        ttk.Label(login_card, text="验证码:").pack(side="left")
        self.e_code = ttk.Entry(login_card, width=9)
        self.e_code.pack(side="left", padx=4)
        btnrow = ttk.Frame(card)
        btnrow.pack(fill="x", pady=(2, 8))
        ttk.Button(btnrow, text="🌐 打开登录页（只用来收验证码）",
                   command=lambda: webbrowser.open(LOGIN_PAGE),
                   **self._o("secondary-outline")).pack(side="left", padx=(0, 8))
        ttk.Button(btnrow, text="登录并获取 Token", command=self.do_login,
                   **self._o("info")).pack(side="left")

        ttk.Label(card, text="③ 抓包: 抓库街区 App 请求头里的 token 和 did，填到「签到」页左侧",
                  **self._o("secondary"), wraplength=560).pack(anchor="w", pady=(6, 0))

        self.login_status = ttk.Label(f, text="", font=("Microsoft YaHei UI", 10, "bold"),
                                      wraplength=560, justify="left")
        self.login_status.pack(anchor="w", padx=4, pady=10)

    def embedded_login(self):
        try:
            import webview  # noqa
        except ImportError:
            messagebox.showinfo("库街区签到助手",
                                "当前构建未内置内嵌浏览器组件，请改用方式②："
                                "在浏览器打开登录页仅点【获取验证码】收短信，"
                                "然后回到程序填手机号+验证码登录（不要在浏览器里登录）")
            webbrowser.open(LOGIN_PAGE)
            return
        self.login_status.configure(text="内嵌登录窗口已打开，请在窗口内完成登录…")

        HOOK_JS = """
        (function(){
          if (window.__kuro_hooked) return 'hooked';
          window.__kuro_token = '';
          window.__kuro_did = '';
          window.__kuro_login = '';
          var FAKE = JSON.stringify({code:500, msg:'请回到库街区签到助手窗口完成登录', data:null});
          function pick(t){ try {
            t = String(t);
            var m = t.match(/eyJ[A-Za-z0-9_\\-\\.]{30,}/);
            if (m) window.__kuro_token = m[0];
          } catch(e){} }
          function captureLogin(b){ try {
            if (!b || window.__kuro_login) return;
            b = String(b);
            if (/["']?mobile["']?\\s*[=:]/.test(b) && /["']?code["']?\\s*[=:]/.test(b)) {
              window.__kuro_login = b;
            }
          } catch(e){} }
          if (window.fetch) {
            var of = window.fetch;
            window.fetch = function(){ var p;
              try {
                var u = String(arguments[0] && arguments[0].url || arguments[0]);
                if (u.indexOf('sdkLogin') >= 0) {
                  captureLogin(arguments[1] && arguments[1].body);
                  return Promise.resolve(new Response(FAKE, {status: 200,
                      headers: {'content-type': 'application/json'}}));
                }
                p = of.apply(this, arguments);
                if (u.indexOf('/user/login') >= 0) {
                  p.then(function(r){ r.clone().text().then(pick); }); }
              } catch(e){ p = of.apply(this, arguments); }
              return p; };
          }
          var xo = XMLHttpRequest.prototype.open, xs = XMLHttpRequest.prototype.send;
          XMLHttpRequest.prototype.open = function(m,u){ this.__u = String(u); return xo.apply(this, arguments); };
          XMLHttpRequest.prototype.send = function(body){ var self = this;
            try {
              if (self.__u && self.__u.indexOf('sdkLogin') >= 0) {
                captureLogin(body);
                var txt = FAKE;
                setTimeout(function(){ try {
                  Object.defineProperty(self, 'readyState', {value: 4, configurable: true});
                  Object.defineProperty(self, 'status', {value: 200, configurable: true});
                  Object.defineProperty(self, 'statusText', {value: 'OK', configurable: true});
                  Object.defineProperty(self, 'responseText', {value: txt, configurable: true});
                  Object.defineProperty(self, 'response', {value: txt, configurable: true});
                  self.dispatchEvent(new Event('readystatechange'));
                  self.dispatchEvent(new Event('load'));
                  self.dispatchEvent(new Event('loadend'));
                } catch(e){} }, 30);
                return;
              }
            } catch(e){}
            return xs.apply(this, arguments); };
          window.__kuro_hooked = true;
          return 'ok';
        })()
        """
        READ_JS = """
        (function(){ try {
          return JSON.stringify({login: window.__kuro_login || '',
                                 token: window.__kuro_token || '',
                                 did: window.__kuro_did || ''});
        } catch(e){ return JSON.stringify({login: '', token: '', did: ''}); } })()
        """
        OPEN_LOGIN_JS = """
        (function(){
          try {
            if (document.querySelector('.login-dialog')) return 'open';
            var els = document.querySelectorAll('button, a, span, div, [class*="login"]');
            for (var i = 0; i < els.length; i++) {
              var el = els[i];
              if (!el.offsetParent) continue;
              var t = (el.textContent || '').replace(/\\s/g, '');
              if (t === '登录') { el.click(); return 'clicked'; }
            }
          } catch(e){}
          return 'not-found';
        })()
        """
        import webview

        win = webview.create_window("库街区登录：滑块→获取验证码→填短信码→点登录（点完窗口会自动关闭）",
                                    LOGIN_PAGE, maximized=True)
        win.events.loaded += lambda: win.evaluate_js(HOOK_JS)

        def poll():
            import time
            import uuid
            import re as _re
            open_tries = 0
            handled_login = False
            for _ in range(1200):  # 最长等 30 分钟
                time.sleep(1.5)
                try:
                    if open_tries < 20:
                        # 登录是页面上的弹窗，自动帮用户点开
                        r_open = win.evaluate_js(OPEN_LOGIN_JS)
                        open_tries += 1
                        if r_open == "clicked":
                            self.root.after(0, lambda: self.login_status.configure(
                                text="已自动打开登录窗口：请在窗口里完成滑块并获取验证码",
                                foreground="#0099db"))
                    login_body = ""
                    token = ""
                    did = ""
                    r = win.evaluate_js(READ_JS)
                    if isinstance(r, str):
                        try:
                            obj = json.loads(r)
                            login_body = obj.get("login", "") or ""
                            token = obj.get("token", "") or ""
                            did = obj.get("did", "") or ""
                        except Exception:
                            token = r
                    elif isinstance(r, dict):
                        login_body = r.get("login", "") or ""
                        token = r.get("token", "") or ""
                        did = r.get("did", "") or ""
                except Exception:
                    return  # 窗口已关闭

                # 首选：拦截到网页登录请求（手机号+验证码），关闭窗口并由程序用 App 方式重放
                if login_body and not handled_login:
                    mb = _re.search(r'mobile["\']?\s*[=:]\s*["\']?(\d{11})', login_body)
                    cd = _re.search(r'["\']?code["\']?\s*[=:]\s*["\']?(\d{4,8})', login_body)
                    mobile = mb.group(1) if mb else ""
                    sms_code = cd.group(1) if cd else ""
                    if not (mobile and sms_code):
                        continue  # 没截全，等下一次提交
                    handled_login = True
                    try:
                        win.destroy()  # 点了登录就关窗口，剩下的交给程序
                    except Exception:
                        pass
                    self.root.after(0, lambda: self.login_status.configure(
                        text="已截获登录请求，正在用 App 方式登录并获取 token…",
                        foreground="#0099db"))
                    devcode = uuid.uuid4().hex

                    def _replay():
                        try:
                            tk = sdk_login(devcode, mobile, sms_code)
                        except Exception as e:
                            self.root.after(0, lambda err=e: self.login_status.configure(
                                text=f"⚠ App 方式登录失败：{err}，请重新打开内嵌登录窗口再试一次",
                                foreground="#e03131"))
                            return
                        self.root.after(0, lambda t_=tk, d_=devcode:
                                        self._apply_web_token(t_, d_))
                    threading.Thread(target=_replay, daemon=True).start()
                    return

                if token.startswith("eyJ"):
                    self.root.after(0, lambda tk_=token, dd_=did:
                                    self._apply_web_token(tk_, dd_))
                    try:
                        win.destroy()
                    except Exception:
                        pass
                    return
        threading.Thread(target=poll, daemon=True).start()
        webview.start()

    def _apply_web_token(self, token, did=""):
        self.e_token.delete(0, "end")
        self.e_token.insert(0, token)
        if not did:
            # 网页版前端不暴露 did；参考开源实现，devCode 可为随机值
            import uuid
            did = uuid.uuid4().hex
        self.e_did.delete(0, "end")
        self.e_did.insert(0, did)
        self.save()
        self.login_status.configure(text="✅ 已捕获登录 token 和 did 并保存，正在签到…",
                                    foreground="#2fb344")
        self._wake.set()

    def _set_status(self, text, state="idle"):
        def _do():
            self.status.configure(state="normal")
            self.status.delete("1.0", "end")
            self.status.insert("1.0", f"[{datetime.now():%m-%d %H:%M:%S}] {text}", state)
            self.status.configure(state="disabled")
        self.root.after(0, _do)

    def save(self):
        cfg = load_config()
        cfg["token"] = self.e_token.get().strip()
        cfg["did"] = self.e_did.get().strip()
        try:
            cfg["phone"] = self.e_mobile.get().strip()
        except AttributeError:
            pass
        save_config(cfg)
        messagebox.showinfo("库街区签到助手", "已保存")

    def manual(self):
        self.save()
        self._wake.set()

    def toggle_autostart(self):
        try:
            set_autostart(self.var_autostart.get())
        except Exception as e:
            self.var_autostart.set(False)
            messagebox.showerror("库街区签到助手", f"设置开机启动失败: {e}")

    def do_login(self):
        mobile, code = self.e_mobile.get().strip(), self.e_code.get().strip()
        if not mobile or not code:
            messagebox.showwarning("库街区签到助手", "请先填手机号和验证码")
            return
        self.login_status.configure(text="登录中…")

        def work():
            devcode = os.urandom(16).hex().upper()
            try:
                token = sdk_login(devcode, mobile, code)
                self.root.after(0, lambda: (self.e_token.delete(0, "end"),
                                            self.e_token.insert(0, token),
                                            self.e_did.delete(0, "end"),
                                            self.e_did.insert(0, devcode),
                                            self.save(),
                                            self.login_status.configure(
                                                text="✅ 登录成功，token 已自动填入并保存",
                                                foreground="#2fb344"),
                                            self._wake.set()))
            except Exception as e:
                self.root.after(0, lambda: self.login_status.configure(
                    text=f"❌ {e}", foreground="#e03131"))
        threading.Thread(target=work, daemon=True).start()

    def _loop(self):
        forced = False
        while True:
            cfg = load_config()
            token, did = (cfg.get("token") or "").strip(), (cfg.get("did") or "").strip()
            state = load_config()
            if not token or not did:
                self._set_status("未配置 token/did，请在上方填写后保存；或用右侧手机验证码登录", "idle")
            elif state.get("last_success_date") == today_str() and not forced:
                self._set_status(f"{today_str()} 今日已签到过，无需重复签到", "already")
            else:
                self._set_status("正在签到…", "running")
                r = run_checkin(token, did)
                ts = f"{datetime.now():%m-%d %H:%M}"
                if r["ok"] and not r["already"]:
                    cfg2 = load_config()
                    cfg2["last_success_date"] = today_str()
                    save_config(cfg2)
                    self._set_status(f"✅ {ts} {r['message']}", "success")
                elif r["already"]:
                    cfg2 = load_config()
                    cfg2["last_success_date"] = today_str()
                    save_config(cfg2)
                    self._set_status(f"ℹ️ {today_str()} {r['message']}", "already")
                else:
                    self._set_status(f"❌ {ts} {r['message']}", "fail")
            forced = False
            self._wake.wait(timeout=30 * 60)
            if self._wake.is_set():
                self._wake.clear()
                forced = True


def main():
    if "--cli" in sys.argv:
        cli_mode()
        return
    if ttkb:
        root = ttkb.Window(title="库街区签到助手 v1.1.0", themename="flatly")
    else:
        root = tk.Tk()
        root.title("库街区签到助手 v1.1.0")
    App(root)
    if "--minimized" in sys.argv:
        root.iconify()
    root.mainloop()


if __name__ == "__main__":
    main()

# OKWW 库街区自动签到

《鸣潮》库街区每日自动签到，提供两种用法：

- **OKWW 插件**：装进 OKWW（鸣潮自动化助手），打开 OKWW 就自动签到
- **独立版 `KuroCheckin.exe`**：不装 OKWW 也能用，双击即用

> 项目不会修改 OKWW 本体，只在 `ok_import/` 目录添加签到脚本。请在了解相关风险后按需使用。

## 功能

- 打开 OKWW（或独立版程序）自动完成库街区游戏签到，跨天自动补签，无需启动游戏
- 实时显示签到状态：✅ 签到成功 / ℹ️ 今日已签到过 / ❌ 签到失败
- 卡片上可填 token，修改自动保存，支持「立即签到」
- 独立版支持手机验证码登录，不用抓包也能拿 token

## OKWW 版安装

1. 安装 [OKWW](https://github.com/ok-oldking/ok-wuthering-waves)（本脚本在 v3.3.68 下验证通过）
2. 下载仓库中的 `kuro-checkin/` 文件夹（或 Release 里的 `kuro-checkin.zip` 解压），整个文件夹复制到 OKWW 数据目录下（没有 `ok_import` 文件夹就自己建一个）：

   ```text
   C:\Users\<你的用户名>\AppData\Local\ok-ww\data\apps\ok-ww\working\ok_import\kuro-checkin
   ```

3. 重启 OKWW，任务页出现「库街区签到」卡片，填入 token 即可（见下文）

## 独立版 KuroCheckin.exe

从 [Releases](../../releases) 下载 `KuroCheckin.exe`，双击即用。

**方式一：手机验证码登录（推荐，不用抓包）**

1. 点「🚀 打开内嵌登录窗口」，程序会自动弹出库街区的登录窗口
2. 在窗口里：划滑块 → 点【获取验证码】→ 填收到的短信码 → 点【登录】
3. 点完登录窗口自动关闭，token 自动填好并开始签到

> 登录就在程序弹出的窗口里完成，**不要自己另开 Chrome/Edge 去登录**，那样拿不到能签到的 token。

**方式二：填现成的 token**

如果已经有 token（比如从手机抓包获得），直接填到「签到」页保存即可。

**小工具**

- 勾选「开机自动启动」：每天开机自动签到
- 命令行模式：`KuroCheckin.exe --cli`，不弹窗口直接签到一次，适合搭配任务计划程序定时跑

## token 是什么，去哪拿

token 就是库街区的登录凭证，程序拿它替你签到。两种获取方式：

- **独立版用户**：直接用上面的手机验证码登录，程序自动搞定
- **OKWW 插件用户 / 想手动填的**：用抓包软件（Fiddler、Charles 等）抓一次库街区 App 的请求，在发往 `api.kurobbs.com` 的请求头里复制 `token`（`eyJ...` 开头的长串）和 `did`（设备码），填进卡片即可

> token 在别的设备登录 App 后会失效，提示失效后重新获取一次就行。

## 常见问题

**独立版登录时点了【登录】没反应 / 网页提示失败？**
正常现象——登录请求由程序接管，网页本身的提示不用管，看程序状态栏即可。

**签到提示 token 失效？**
重新走一遍验证码登录（独立版），或重新抓包更新 token（OKWW 插件）。

**会不会封号？**
签到用的是官方 App 同款接口，但第三方工具始终有风险，请自行评估。

## 更新日志

各版本变更见 [`CHANGELOG.md`](CHANGELOG.md)。

## 致谢

- 感谢 [老王同学 OK](https://github.com/ok-oldking/ok-wuthering-waves) 开发 OK-WW 及其脚本机制
- 感谢 [Loping151/RoverSign](https://github.com/Loping151/RoverSign)、[Ko-Koa/Kuro_login](https://github.com/Ko-Koa/Kuro_login) 开源的库街区接口实现
- 感谢 [IceHe/okww-xwuid-echo-score](https://github.com/IceHe/okww-xwuid-echo-score) 提供的导入脚本结构参考
- 本项目按 GNU GPL v2 发布，详见 [`LICENSE`](LICENSE)

问题反馈和改进建议欢迎通过仓库 Issue 提交。

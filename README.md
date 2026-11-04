# OKWW 库街区自动签到

这是一个通过 OKWW（ok-script 机制）加载的《鸣潮》**库街区每日游戏签到**功能。它复用 OKWW 的导入脚本机制，在后台完成库街区的游戏签到，签到接口实现参考 [Loping151/RoverSign](https://github.com/Loping151/RoverSign)。

> 当前版本为 **1.0.0**。请在了解相关风险后按需使用。项目不会修改 OKWW 宿主程序源码，仅向 `ok_import/` 目录添加导入脚本。

## 功能

打开 OKWW 后，工具会在后台自动完成一次库街区游戏签到，之后每 30 分钟检查一次日期，跨天后自动重新签到。签到状态显示在「库街区签到」卡片顶部：

- 🟢 签到成功：`✅ 11-05 08:00 签到成功: 角色名 签到成功（请求成功）`
- 🔵 今日已签到：`ℹ️ 2026-11-05 今日已签到过，无需重复签到`
- 🔴 签到失败：`❌ 11-05 08:00 签到失败: token 已失效，请重新抓包更新`
- ⚪ 签到中：`⏳ 正在签到…`

签到成功或失败会同时弹出 OKWW 系统通知。卡片还提供：

- **token / did 输入框**：修改后自动保存，重启 OKWW 后依然生效；
- **立即签到**按钮：随时手动触发一次强制签到；
- **自动签到开关**：关闭后停止后台签到线程的自动尝试。

整个签到流程不依赖游戏画面，无需启动或捕获鸣潮窗口。

## 安装

### 1. 安装 OKWW

本功能依赖 OKWW 的导入脚本（OKScript）机制。请先从 [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves) 了解并安装 OKWW；使用前请阅读其说明并自行评估风险。

本脚本已在 OKWW **v3.3.68**（China 配置）下开发验证，其他版本未经测试。

### 2. 安装签到脚本

下载仓库中的 `kuro-checkin/` 文件夹（或 Release 中的 `kuro-checkin.zip` 解压），将整个文件夹复制到 OKWW 数据目录下的：

```text
data/apps/ok-ww/working/ok_import/kuro-checkin
```

例如默认安装路径下为：

```text
C:\Users\<你的用户名>\AppData\Local\ok-ww\data\apps\ok-ww\working\ok_import\kuro-checkin
```

重启 OKWW，任务页会出现「库街区签到」卡片。

### 3. 获取并填写 token / did

需要抓一次库街区 App 的 HTTPS 请求（Fiddler、Charles、mitmproxy 等均可，开启 HTTPS 解密）：

1. 手机配置代理并信任证书后，打开库街区 App；
2. 在请求列表中找任意发往 `api.kurobbs.com` 的 POST 请求；
3. 在请求头中复制两个值：
   - `token`：`eyJ...` 开头的长 JWT 字符串；
   - `did`：设备码（40 位左右的大写十六进制字符串）；
4. 打开 OKWW 的「库街区签到」卡片，填入 token 和 did，修改后即时保存。

> **token 有效期**：库街区 token 在新设备登录 App 后会被刷新失效（状态栏会提示 `token 已失效，请重新抓包更新`）。失效后重新抓包，在卡片上更新 token 即可。

## 签到接口说明

调用链参考开源项目 [Loping151/RoverSign](https://github.com/Loping151/RoverSign)：

| 步骤 | 端点 | 说明 |
| --- | --- | --- |
| 1 | `POST /user/mineV2` | 验证 token，获取库街区 userId |
| 2 | `POST /user/role/findRoleList` | gameId=3，获取鸣潮角色与 serverId |
| 3 | `POST /encourage/signIn/initSignInV2` | 查询今日是否已签到（`isSigIn`） |
| 4 | `POST /encourage/signIn/v2` | 执行游戏签到 |

常见返回码：`200` 签到成功；`1511` 今日已签到；`220` token 失效；`1501` 未查询到活动配置。

> **踩坑记录**：`/encourage/signIn/v2` 的 `reqMonth` 参数必须是**两位月份**（如 `"11"`），传 `"202611"` 会返回 `1501 未查询到活动配置`。

签到请求头（`source`、`version`、`User-Agent`、`devCode`、`did` 等）均模拟库街区 App（KuroGameBox）客户端。鸣潮国服 `serverId` 为固定值 `76402e5b20be2c39f095a152090afddc`；角色 ID 不小于 `200000000` 时按渠道服处理（`919752ae5ea09c1ced910dd668a63ffb`）。

## 目录结构

源码位于 [`kuro-checkin/`](kuro-checkin/)，全部使用 Python 标准库，无第三方依赖：

| 文件 | 作用 |
| --- | --- |
| `manifest.json` | OKWW 导入脚本声明（名称与版本） |
| `kuro_api.py` | 签到 API 封装：token 验证、角色获取、签到与返回码处理 |
| `kuro_checkin_task.py` | 任务与界面：后台签到线程、状态着色显示、立即签到、配置输入行 |

运行时会在脚本目录下生成两个文件，包含账号相关信息（角色名、签到日期），**请勿上传或分享**：

- `checkin_log.md`：每次签到的结果日志；
- `checkin_state.json`：记录最近一次成功签到的日期，用于跨天判断。

## 对 OKWW v3.3.68 的适配说明

本脚本对宿主做了以下兼容处理，均不修改 OKWW 自身文件：

- 导入任务的加载晚于主窗口 Script 编辑页的创建时机，点击任务卡片的「编辑」会报 `AttributeError`；脚本已对该按钮做懒创建修复，首次点击会自动创建 "Script" 页并加载源码；
- 宿主配置控件会按文本长度设置输入框固定宽度，170 字符的 token 会把卡片布局撑出窗口；脚本已改为自建固定宽度（520px）输入行，超长内容在输入框内部横向滚动；
- 该版本不支持配置项的 `hidden` 类型，token / did 因此使用自建输入行实现。

## 致谢与许可

- 感谢 [老王同学 OK](https://github.com/ok-oldking/ok-wuthering-waves) 开发 OKWW 及其 OKScript 机制。
- 感谢 [Loping151/RoverSign](https://github.com/Loping151/RoverSign) 开源库街区签到接口实现，本项目参考其 API 调用方式（未直接复制其代码）。
- 感谢 [IceHe/okww-xwuid-echo-score](https://github.com/IceHe/okww-xwuid-echo-score) 的导入脚本结构与说明文档写法，本项目参考其组织方式。
- 本项目代码按 GNU GPL v2 发布，详见 [`LICENSE`](LICENSE)。第三方项目及其代码仍分别受各自许可证约束。

问题反馈和改进建议欢迎通过仓库 Issue 提交。

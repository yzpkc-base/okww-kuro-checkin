import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, 'checkin_log.md')
STATE_FILE = os.path.join(SCRIPT_DIR, 'checkin_state.json')
GAME_ID = '3'
WUWA_SERVER_ID = '76402e5b20be2c39f095a152090afddc'
WUWA_SERVER_ID_NET = '919752ae5ea09c1ced910dd668a63ffb'
KURO_VERSION = '3.1.3'
IP = '10.0.2.233'
_URL_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)  KuroGameBox/3.1.3'
URL_MINE = 'https://api.kurobbs.com/user/mineV2'
URL_ROLE_LIST = 'https://api.kurobbs.com/user/role/findRoleList'
URL_SIGN_IN = 'https://api.kurobbs.com/encourage/signIn/v2'
URL_SIGN_INIT = 'https://api.kurobbs.com/encourage/signIn/initSignInV2'
USER_INFO_HEADERS = {'osversion': 'Android', 'countrycode': 'CN', 'ip': IP, 'model': '2211133C', 'source': 'android', 'lang': 'zh-Hans', 'version': '1.0.9', 'versioncode': '1090', 'content-type': 'application/x-www-form-urlencoded', 'accept-encoding': 'gzip', 'user-agent': 'okhttp/3.10.0'}
GAME_HEADERS = {'source': 'ios', 'version': KURO_VERSION, 'User-Agent': _URL_UA, 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', 'devCode': f'{IP}, {_URL_UA}', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'zh-CN,zh-Hans;q=0.9', 'Connection': 'keep-alive'}

def _post(url, headers, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_user_id(token, did):
    h = dict(USER_INFO_HEADERS)
    h['devcode'] = did
    h['token'] = token
    r = _post(URL_MINE, h, {})
    if r.get('code') != 200 or not r.get('data'):
        raise RuntimeError(f"token 验证失败 code={r.get('code')} {r.get('msg')}")
    uid = r['data'].get('mine', {}).get('userId')
    if not uid:
        raise RuntimeError('未获取到 userId')
    return int(uid)

def get_wuwa_role(token, did):
    h = dict(USER_INFO_HEADERS)
    h['devcode'] = did
    h['token'] = token
    r = _post(URL_ROLE_LIST, h, {'gameId': GAME_ID})
    if r.get('code') != 200 or not r.get('data'):
        raise RuntimeError(f"获取角色失败 code={r.get('code')} {r.get('msg')}")
    roles = r['data']
    if not roles:
        raise RuntimeError('该账号未绑定鸣潮游戏角色')
    role = roles[0]
    if not role.get('serverId'):
        role['serverId'] = WUWA_SERVER_ID
    return role

def do_sign_in(token, did, role):
    server_id = WUWA_SERVER_ID_NET if int(role['roleId']) >= 200000000 else role.get('serverId') or WUWA_SERVER_ID
    h = dict(GAME_HEADERS)
    h['token'] = token
    h['did'] = did
    h['b-at'] = ''
    h['devcode'] = ''
    try:
        r = _post(URL_SIGN_INIT, h, {'gameId': GAME_ID, 'serverId': server_id, 'roleId': str(role['roleId'])})
        if r.get('code') == 200 and isinstance(r.get('data'), dict) and r['data'].get('isSigIn'):
            return {'code': 1511, 'msg': '今日已签到'}
    except Exception:
        pass
    data = {'gameId': GAME_ID, 'serverId': server_id, 'roleId': str(role['roleId']), 'reqMonth': datetime.now().strftime('%m')}
    return _post(URL_SIGN_IN, h, data)

def today_str():
    return datetime.now().strftime('%Y-%m-%d')

def _append_log(text):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'## {datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n')
    except Exception:
        pass

def load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def run_checkin(token, did):
    lines = []
    try:
        user_id = get_user_id(token, did)
        lines.append(f'token/did 验证通过 userId={user_id}')
        role = get_wuwa_role(token, did)
        role_name = role.get('roleName', '?')
        lines.append(f"角色 {role_name} roleId={role.get('roleId')}")
        r = do_sign_in(token, did, role)
        code, msg = (r.get('code'), r.get('msg', ''))
        if code == 200:
            lines.append('✅ 签到成功')
            _append_log('\n'.join(lines))
            return {'ok': True, 'already': False, 'message': f'{role_name} 签到成功', 'role': role_name}
        elif code == 1511:
            lines.append('ℹ️ 今日已签到')
            _append_log('\n'.join(lines))
            return {'ok': True, 'already': True, 'message': f'{role_name} 今日已签到', 'role': role_name}
        elif code == 220:
            _append_log('\n'.join(lines) + f'\n❌ token 失效 code=220')
            return {'ok': False, 'already': False, 'message': 'token 已失效，请重新抓包更新'}
        else:
            _append_log('\n'.join(lines) + f'\n❌ 失败 code={code} {msg}')
            return {'ok': False, 'already': False, 'message': f'失败 code={code} {msg}'}
    except Exception as e:
        _append_log('\n'.join(lines) + f'\n❌ 异常 {e}')
        return {'ok': False, 'already': False, 'message': f'异常: {e}'}

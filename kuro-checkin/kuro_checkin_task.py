import threading
from datetime import datetime
from ok import BaseTask
from ok.gui.Communicate import communicate
from kuro_api import load_state, run_checkin, save_state, today_str
CHECK_INTERVAL_SECONDS = 30 * 60

class KuroCheckinTask(BaseTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '库街区签到'
        self.description = '打开 OKWW 自动完成库街区(鸣潮)每日签到，下方实时显示状态：✅ 签到成功 / ℹ️ 今日已签到 / ❌ 签到失败'
        self.default_config.update({'启用自动签到': True, 'token': '', 'did': ''})
        self.config_type = {'立即签到': {'type': 'button', 'buttons': [{'text': '立即签到', 'callback': self.manual_sign}]}}
        self.config_description = {'启用自动签到': '打开 OKWW 后自动签到，跨天后自动补签', 'token': '', 'did': ''}
        self.status_text = '启动中…'
        self.status_state = 'running'
        self._thread = None
        self._wake = threading.Event()

    def on_create(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True, name='kuro-checkin')
            self._thread.start()

    def run(self):
        self.manual_sign()

    def open_editor(self):
        from ok import og
        from qfluentwidgets import FluentIcon
        mw = og.main_window
        tab = getattr(mw, 'edit_task_tab', None)
        if tab is None:
            from ok.gui.tasks.EditTaskTab import EditTaskTab
            tab = EditTaskTab()
            mw.edit_task_tab = tab
            mw.addSubInterface(tab, FluentIcon.EDIT, mw.tr('Script'))
        tab.load_task(self)
        mw.switchTo(tab)

    def manual_sign(self):
        self._wake.set()

    def _set_status(self, text, state='idle'):
        self.status_text = text
        self.status_state = state
        try:
            communicate.task.emit(self)
        except Exception:
            pass

    def _notify(self, message, error=False):
        try:
            communicate.notification.emit(message, '库街区签到', error, True, False, None)
        except Exception:
            pass

    def _loop(self):
        forced = False
        while True:
            status, st = (None, 'idle')
            try:
                enabled = bool(self.config.get('启用自动签到', True))
                token = (self.config.get('token') or '').strip()
                did = (self.config.get('did') or '').strip()
                state = load_state()
                signed_today = state.get('last_success_date') == today_str()
                if not enabled:
                    status, st = ('自动签到已停用', 'off')
                elif not token or not did:
                    status, st = ('未配置 token/did，请在下方填写后点【立即签到】', 'warn')
                elif signed_today and (not forced):
                    status, st = (f'ℹ️ {today_str()} 今日已签到过，无需重复签到', 'already')
                else:
                    self._set_status('⏳ 正在签到…', 'running')
                    r = run_checkin(token, did)
                    ts = f'{datetime.now():%m-%d %H:%M}'
                    if r['ok'] and (not r['already']):
                        state['last_success_date'] = today_str()
                        save_state(state)
                        status, st = (f"✅ {ts} 签到成功: {r['message']}（请求成功）", 'success')
                        self._notify(f"✅ 签到成功: {r['message']}")
                    elif r['already']:
                        state['last_success_date'] = today_str()
                        save_state(state)
                        status, st = (f"ℹ️ {ts} {r['message']}，无需重复签到", 'already')
                    else:
                        status, st = (f"❌ {ts} 签到失败: {r['message']}", 'fail')
                        self._notify(f"❌ 签到失败: {r['message']}", error=True)
            except Exception as e:
                status, st = (f'❌ 签到异常: {e}', 'fail')
            if status:
                self._set_status(status, st)
            forced = False
            self._wake.wait(timeout=CHECK_INTERVAL_SECONDS)
            if self._wake.is_set():
                self._wake.clear()
                forced = True

def _status_html(text, state):
    import html as _html
    colors = {'success': '#2fb344', 'already': '#0099db', 'fail': '#e03131', 'running': '#909296', 'warn': '#f76707', 'off': '#909296', 'idle': '#5c5f66'}
    color = colors.get(state, '#5c5f66')
    safe = _html.escape(str(text))
    return f'<span style="color:{color}; font-weight:600;">{safe}</span>'

def _patch_kuro_task_card():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from ok.gui.tasks.TaskCard import TaskCard
    if getattr(TaskCard, '_kuro_card_patch', False):
        return
    original_init = TaskCard.__init__

    def patched_init(card, task, onetime):
        original_init(card, task, onetime)
        if task.__class__.__name__ != 'KuroCheckinTask':
            return
        for button in (getattr(card, 'start_button', None), getattr(card, 'pause_button', None), getattr(card, 'stop_button', None)):
            if button is not None:
                button.hide()
        card.onetime = False
        edit_button = getattr(card, 'edit_button', None)
        if edit_button is not None:
            try:
                edit_button.clicked.disconnect()
            except Exception:
                pass
            edit_button.clicked.connect(task.open_editor)
        from PySide6.QtWidgets import QHBoxLayout, QLabel as _QLabel, QWidget as _QWidget
        from qfluentwidgets import LineEdit as _LineEdit
        for key in ('token', 'did'):
            host_widget = card.config_widget_by_key.get(key)
            if host_widget is not None:
                host_widget.setVisible(False)
                host_widget.setFixedHeight(0)

        def _make_config_row(key, placeholder):
            row = _QWidget(card)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lab = _QLabel(key, row)
            edit = _LineEdit(row)
            edit.setFixedWidth(520)
            edit.setPlaceholderText(placeholder)
            edit.setText(str(task.config.get(key) or ''))
            edit.textChanged.connect(lambda v, k=key: task.config.__setitem__(k, v))
            lay.addWidget(lab)
            lay.addWidget(edit)
            lay.addStretch(1)
            return row
        host_token = card.config_widget_by_key.get('token')
        idx = card.viewLayout.indexOf(host_token) if host_token is not None else 1
        card.viewLayout.insertWidget(idx, _make_config_row('token', '库街区抓包获取的 token，新设备登录后失效需重新抓包'))
        card.viewLayout.insertWidget(idx + 1, _make_config_row('did', '库街区抓包获取的 did / 设备码'))
        status_label = QLabel(card)
        status_label.setTextFormat(Qt.RichText)
        status_label.setWordWrap(True)

        def refresh(t):
            if t is task:
                status_label.setText(_status_html(task.status_text, getattr(task, 'status_state', 'idle')))
        communicate.task.connect(refresh)
        refresh(task)
        card.viewLayout.insertWidget(0, status_label)
        card.setExpand(True)
        card._kuro_status_label = status_label
    TaskCard.__init__ = patched_init
    TaskCard._kuro_card_patch = True
_patch_kuro_task_card()

"""
Login Dialog for adding accounts - React style step-based authentication.

FIX: Replaced api_client (HTTP) with data_service (direct service calls).
The old code made HTTP requests to a FastAPI server that is not running in
the unified application, causing every login attempt to fail with a
ConnectionError.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from toast import toast_success, toast_error, toast_info
from data_service import get_data_service

COLORS = {
    'bg_primary':       '#0D1117',
    'bg_secondary':     '#161B22',
    'bg_tertiary':      '#21262D',
    'bg_hover':         '#30363D',
    'text_primary':     '#F0F6FC',
    'text_secondary':   '#8B949E',
    'text_muted':       '#6E7681',
    'border':           '#30363D',
    'accent_blue':      '#58A6FF',
    'accent_blue_dark': '#1F6FEB',
    'accent_green':     '#3FB950',
    'accent_red':       '#F85149',
}


class LoginDialog(QDialog):
    """Step-based login dialog (phone → code → optional 2FA password)."""

    account_added = pyqtSignal()

    def __init__(self, parent=None, proxies=None):
        super().__init__(parent)
        self.data = get_data_service()   # FIX: was get_api_client()
        self.proxies = proxies or []
        self.step = 'phone'
        self.phone = ''
        self.phone_code_hash = ''
        self.selected_proxy_id = None
        self.current_code = ''
        self.loading = False

        self.setWindowTitle("Login to Telegram")
        self.setMinimumWidth(380)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit, QComboBox {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 12px;
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {COLORS['accent_blue']};
            }}
            QComboBox {{
                padding: 8px 10px;
            }}
            QComboBox::drop-down {{ border: none; padding-right: 10px; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['accent_blue']};
            }}
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 20px;
                color: {COLORS['text_primary']};
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {COLORS['bg_hover']}; }}
            QPushButton#primary {{
                background-color: {COLORS['accent_blue']};
                border: none;
                color: white;
            }}
            QPushButton#primary:hover {{ background-color: {COLORS['accent_blue_dark']}; }}
            QPushButton:disabled {{ opacity: 0.5; }}
        """)
        self.setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Login to Telegram")
        title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {COLORS['text_primary']}; margin-bottom: 8px;")
        layout.addWidget(title)

        # Error banner (hidden by default)
        self.error_frame = QFrame()
        self.error_frame.setStyleSheet("QFrame { background-color: #7f1d1d; border-radius: 8px; padding: 10px; }")
        error_layout = QHBoxLayout(self.error_frame)
        error_layout.setContentsMargins(12, 10, 12, 10)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #fecaca; font-size: 13px;")
        error_layout.addWidget(self.error_label)
        self.error_frame.setVisible(False)
        layout.addWidget(self.error_frame)

        # Step content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(12)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.action_btn = QPushButton("Send Code")
        self.action_btn.setObjectName("primary")
        self.action_btn.clicked.connect(self.handle_action)
        button_layout.addWidget(self.action_btn)

        layout.addLayout(button_layout)
        self.show_phone_step()

    # ------------------------------------------------------------------
    # Step rendering
    # ------------------------------------------------------------------

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_phone_step(self):
        self.step = 'phone'
        self._clear_content()
        self.clear_error()

        self.content_layout.addWidget(QLabel("Phone Number"))
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1234567890")
        self.content_layout.addWidget(self.phone_input)

        self.content_layout.addWidget(QLabel("Proxy (optional)"))
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("No proxy", None)
        for proxy in self.proxies:
            self.proxy_combo.addItem(f"{proxy.scheme}://{proxy.host}:{proxy.port}", proxy.id)
        self.content_layout.addWidget(self.proxy_combo)

        self.action_btn.setText("Send Code")
        self.phone_input.setFocus()

    def show_code_step(self):
        self.step = 'code'
        self._clear_content()
        self.clear_error()

        info = QLabel(f"Enter the code sent to {self.phone}")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        self.content_layout.addWidget(info)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("12345")
        self.content_layout.addWidget(self.code_input)

        self.action_btn.setText("Verify")
        self.code_input.setFocus()

    def show_password_step(self):
        self.step = 'password'
        self._clear_content()
        self.clear_error()

        info = QLabel("2FA password required")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        self.content_layout.addWidget(info)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.content_layout.addWidget(self.password_input)

        self.action_btn.setText("Submit")
        self.password_input.setFocus()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def show_error(self, message: str):
        self.error_label.setText(message)
        self.error_frame.setVisible(True)

    def clear_error(self):
        self.error_frame.setVisible(False)

    def set_loading(self, loading: bool):
        self.loading = loading
        self.action_btn.setEnabled(not loading)
        loading_texts = {'phone': 'Sending…', 'code': 'Verifying…', 'password': 'Submitting…'}
        action_texts  = {'phone': 'Send Code', 'code': 'Verify',      'password': 'Submit'}
        self.action_btn.setText(
            loading_texts.get(self.step, 'Loading…') if loading
            else action_texts.get(self.step, 'Continue')
        )

    # ------------------------------------------------------------------
    # Action routing
    # ------------------------------------------------------------------

    def handle_action(self):
        if self.step == 'phone':
            self._start_login()
        elif self.step in ('code', 'password'):
            self._complete_login()

    # ------------------------------------------------------------------
    # Login steps – now call data_service directly instead of HTTP POST
    # ------------------------------------------------------------------

    def _start_login(self):
        phone = self.phone_input.text().strip()
        if not phone:
            self.show_error("Please enter a phone number")
            return

        self.phone = phone
        self.selected_proxy_id = self.proxy_combo.currentData()
        self.set_loading(True)

        try:
            # FIX: was self.api.post(Endpoints.LOGIN_START, {...})
            response = self.data.login_start(phone, self.selected_proxy_id)
            self.phone_code_hash = response.get("phone_code_hash", "")
            self.set_loading(False)
            self.show_code_step()
            toast_info("Code sent! Check your Telegram app.")
        except Exception as exc:
            self.set_loading(False)
            self.show_error(str(exc) or "Failed to send code")

    def _complete_login(self):
        code = ''
        password = None

        if self.step == 'code':
            code = self.code_input.text().strip()
            if not code:
                self.show_error("Please enter the code")
                return
            self.current_code = code
        elif self.step == 'password':
            code = self.current_code
            password = self.password_input.text().strip()
            if not password:
                self.show_error("Please enter your 2FA password")
                return

        self.set_loading(True)

        try:
            # FIX: was self.api.post(Endpoints.LOGIN_COMPLETE, {...})
            self.data.login_complete(
                self.phone,
                code,
                self.phone_code_hash,
                password or None,
                self.selected_proxy_id,
            )
            toast_success("Account logged in successfully!")
            self.account_added.emit()
            self.accept()
        except Exception as exc:
            error_str = str(exc)
            if '2FA' in error_str or 'password' in error_str.lower():
                self.set_loading(False)
                self.show_password_step()
                self.show_error("2FA password required")
            else:
                self.set_loading(False)
                self.show_error(error_str or "Login failed")

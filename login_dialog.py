"""
Login Dialog for adding accounts - React style step-based authentication
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from toast import toast_success, toast_error, toast_info
from api_client import get_api_client, Endpoints

# Color palette (same as main.py to avoid circular import)
COLORS = {
    'bg_primary': '#0D1117',
    'bg_secondary': '#161B22',
    'bg_tertiary': '#21262D',
    'bg_hover': '#30363D',
    'text_primary': '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted': '#6E7681',
    'border': '#30363D',
    'accent_blue': '#58A6FF',
    'accent_blue_dark': '#1F6FEB',
    'accent_green': '#3FB950',
    'accent_red': '#F85149',
}


class LoginDialog(QDialog):
    """Step-based login dialog matching React frontend style"""
    
    account_added = pyqtSignal()
    
    def __init__(self, parent=None, proxies=None):
        super().__init__(parent)
        self.api = get_api_client()
        self.proxies = proxies or []
        self.step = 'phone'
        self.phone = ''
        self.phone_code_hash = ''
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
            QLineEdit::placeholder, QComboBox::placeholder {{
                color: {COLORS['text_muted']};
            }}
            QComboBox {{
                padding: 8px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
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
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            QPushButton#primary {{
                background-color: {COLORS['accent_blue']};
                border: none;
                color: white;
            }}
            QPushButton#primary:hover {{
                background-color: {COLORS['accent_blue_dark']};
            }}
            QPushButton:disabled {{
                opacity: 0.5;
            }}
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("Login to Telegram")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {COLORS['text_primary']};
            margin-bottom: 8px;
        """)
        layout.addWidget(title)
        
        # Error display (hidden by default)
        self.error_frame = QFrame()
        self.error_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #7f1d1d;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        error_layout = QHBoxLayout(self.error_frame)
        error_layout.setContentsMargins(12, 10, 12, 10)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #fecaca; font-size: 13px;")
        error_layout.addWidget(self.error_label)
        self.error_frame.setVisible(False)
        layout.addWidget(self.error_frame)
        
        # Stacked content for different steps
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
        
        # Show phone step initially
        self.show_phone_step()
    
    def show_error(self, message):
        self.error_label.setText(message)
        self.error_frame.setVisible(True)
    
    def clear_error(self):
        self.error_frame.setVisible(False)
    
    def set_loading(self, loading):
        self.loading = loading
        self.action_btn.setEnabled(not loading)
        if loading:
            self.action_btn.setText(self.get_loading_text())
        else:
            self.action_btn.setText(self.get_action_text())
    
    def get_loading_text(self):
        texts = {
            'phone': 'Sending...',
            'code': 'Verifying...',
            'password': 'Submitting...'
        }
        return texts.get(self.step, 'Loading...')
    
    def get_action_text(self):
        texts = {
            'phone': 'Send Code',
            'code': 'Verify',
            'password': 'Submit'
        }
        return texts.get(self.step, 'Continue')
    
    def clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def show_phone_step(self):
        self.step = 'phone'
        self.clear_content()
        self.clear_error()
        
        # Phone input
        phone_label = QLabel("Phone Number")
        self.content_layout.addWidget(phone_label)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1234567890")
        self.content_layout.addWidget(self.phone_input)
        
        # Proxy dropdown
        proxy_label = QLabel("Proxy (optional)")
        self.content_layout.addWidget(proxy_label)
        
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("No proxy", None)
        for proxy in self.proxies:
            self.proxy_combo.addItem(f"{proxy.scheme}://{proxy.host}:{proxy.port}", proxy.id)
        self.content_layout.addWidget(self.proxy_combo)
        
        self.action_btn.setText("Send Code")
        self.phone_input.setFocus()
    
    def show_code_step(self):
        self.step = 'code'
        self.clear_content()
        self.clear_error()
        
        # Code info
        info_label = QLabel(f"Enter the code sent to {self.phone}")
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        self.content_layout.addWidget(info_label)
        
        # Code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("12345")
        self.content_layout.addWidget(self.code_input)
        
        self.action_btn.setText("Verify")
        self.code_input.setFocus()
    
    def show_password_step(self):
        self.step = 'password'
        self.clear_content()
        self.clear_error()
        
        # Password info
        info_label = QLabel("2FA password required")
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        self.content_layout.addWidget(info_label)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        self.content_layout.addWidget(self.password_input)
        
        self.action_btn.setText("Submit")
        self.password_input.setFocus()
    
    def handle_action(self):
        if self.step == 'phone':
            self.start_login()
        elif self.step == 'code':
            self.complete_login()
        elif self.step == 'password':
            self.complete_login()
    
    def start_login(self):
        phone = self.phone_input.text().strip()
        if not phone:
            self.show_error("Please enter a phone number")
            return
        
        self.phone = phone
        # Store proxy_id before switching steps
        self.selected_proxy_id = self.proxy_combo.currentData()
        self.set_loading(True)
        
        try:
            response = self.api.post(Endpoints.LOGIN_START, {
                "phone": phone,
                "proxy_id": self.selected_proxy_id
            })
            self.phone_code_hash = response.get("phone_code_hash", "")
            self.set_loading(False)
            self.show_code_step()
            toast_info("Code sent! Check your Telegram app.")
        except Exception as e:
            self.set_loading(False)
            self.show_error(str(e) or "Failed to send code")
    
    def complete_login(self):
        code = ''
        password = ''
        
        if self.step == 'code':
            code = self.code_input.text().strip()
            if not code:
                self.show_error("Please enter the code")
                return
            # Store code for potential 2FA step
            self.current_code = code
        elif self.step == 'password':
            code = getattr(self, 'current_code', '')
            password = self.password_input.text().strip()
            if not password:
                self.show_error("Please enter your 2FA password")
                return
        
        self.set_loading(True)
        
        try:
            self.api.post(Endpoints.LOGIN_COMPLETE, {
                "phone": self.phone,
                "code": code,
                "phone_code_hash": self.phone_code_hash,
                "password": password or None,
                "proxy_id": getattr(self, 'selected_proxy_id', None)
            })
            toast_success("Account logged in successfully!")
            self.account_added.emit()
            self.accept()
        except Exception as e:
            error_str = str(e)
            if '2FA' in error_str or 'password' in error_str.lower():
                self.set_loading(False)
                # Store code before switching to password step
                self.current_code = self.code_input.text().strip() if hasattr(self, 'code_input') else getattr(self, 'current_code', '')
                self.show_password_step()
                self.show_error("2FA password required")
            else:
                self.set_loading(False)
                self.show_error(error_str or "Login failed")

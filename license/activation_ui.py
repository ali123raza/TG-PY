"""
Activation Screen — shown on first run or when license check fails.
Beautiful dark-themed dialog matching the main app style.
"""
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

COLORS = {
    'bg':        '#0D1117',
    'card':      '#161B22',
    'border':    '#30363D',
    'text':      '#F0F6FC',
    'muted':     '#8B949E',
    'blue':      '#58A6FF',
    'blue_dark': '#1F6FEB',
    'green':     '#3FB950',
    'red':       '#F85149',
    'yellow':    '#D29922',
}


class LicenseCheckThread(QThread):
    """Run license check in background — don't freeze UI."""
    result_ready = pyqtSignal(object)  # LicenseResult

    def __init__(self, username: str, password: str, hardware_id: str):
        super().__init__()
        self.username    = username
        self.password    = password
        self.hardware_id = hardware_id

    def run(self):
        try:
            from license.checker import check_license
            result = check_license(self.username, self.password, self.hardware_id)
            self.result_ready.emit(result)
        except Exception as e:
            from license.checker import LicenseResult
            self.result_ready.emit(
                LicenseResult(False, f"Error: {e}"))


class ActivationDialog(QDialog):
    """
    Full-screen activation dialog.
    Returns accepted() if license is valid.
    After acceptance, call .license_result for the result object.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_result = None
        self._thread = None

        from license.hardware import get_hardware_id
        self._hardware_id = get_hardware_id()

        self.setWindowTitle("TG-PY — Activation")
        self.setFixedSize(460, 560)
        # Remove close button — user must activate or app exits
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg']};
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QLineEdit {{
                background-color: {COLORS['card']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px 16px;
                color: {COLORS['text']};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['blue']};
            }}
            QPushButton {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px;
                color: {COLORS['text']};
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #21262D;
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Top banner ────────────────────────────────────────────────────────
        banner = QWidget()
        banner.setFixedHeight(140)
        banner.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #1F6FEB, stop:1 #0D1117);
        """)
        bl = QVBoxLayout(banner)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel("📱")
        logo.setStyleSheet("font-size: 48px; background: transparent;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(logo)

        app_name = QLabel("TG-PY")
        app_name.setStyleSheet("""
            font-size: 28px; font-weight: bold;
            color: white; background: transparent;
        """)
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(app_name)

        layout.addWidget(banner)

        # ── Form ──────────────────────────────────────────────────────────────
        form = QWidget()
        form.setStyleSheet(f"background: {COLORS['bg']};")
        fl = QVBoxLayout(form)
        fl.setSpacing(14)
        fl.setContentsMargins(40, 32, 40, 32)

        title = QLabel("Software Activation")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {COLORS['text']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(title)

        sub = QLabel("Enter your credentials to activate")
        sub.setStyleSheet(
            f"font-size: 13px; color: {COLORS['muted']};")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(sub)
        fl.addSpacing(8)

        # Username
        user_lbl = QLabel("Username")
        user_lbl.setStyleSheet(
            f"font-size: 13px; color: {COLORS['muted']}; font-weight: 500;")
        fl.addWidget(user_lbl)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        fl.addWidget(self.username_input)

        # Password
        pass_lbl = QLabel("Password")
        pass_lbl.setStyleSheet(
            f"font-size: 13px; color: {COLORS['muted']}; font-weight: 500;")
        fl.addWidget(pass_lbl)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.returnPressed.connect(self._do_activate)
        fl.addWidget(self.password_input)

        # Error label (hidden initially)
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(f"""
            color: {COLORS['red']};
            font-size: 12px;
            background: rgba(248,81,73,0.1);
            border: 1px solid rgba(248,81,73,0.3);
            border-radius: 8px;
            padding: 8px 12px;
        """)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setVisible(False)
        fl.addWidget(self.error_lbl)

        # Activate button
        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setFixedHeight(48)
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #58A6FF, stop:1 #1F6FEB);
                border: none; border-radius: 10px;
                color: white; font-size: 15px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #79B8FF, stop:1 #388BFD);
            }}
            QPushButton:disabled {{
                background: #21262D; color: {COLORS['muted']};
            }}
        """)
        self.activate_btn.clicked.connect(self._do_activate)
        fl.addWidget(self.activate_btn)

        # Support note
        support = QLabel("Problems? Contact support to get your credentials.")
        support.setStyleSheet(
            f"font-size: 11px; color: {COLORS['muted']};")
        support.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(support)

        layout.addWidget(form)

    def _do_activate(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username:
            self._show_error("Please enter your username.")
            return
        if not password:
            self._show_error("Please enter your password.")
            return

        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Verifying…")
        self.error_lbl.setVisible(False)

        self._thread = LicenseCheckThread(username, password, self._hardware_id)
        self._thread.result_ready.connect(self._on_result)
        self._thread.start()

    def _on_result(self, result):
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("Activate")

        if result.ok:
            self.license_result = result
            self.accept()   # Only accept() on explicit success
        else:
            # Wrong credentials — show error, NEVER accept
            self.license_result = None
            self._show_error(result.message or "Authentication failed.")

    def closeEvent(self, event):
        # X button clicked — exit app (no bypass)
        import sys
        sys.exit(0)

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.setVisible(True)


class LicenseExpiredDialog(QDialog):
    """Shown when license has expired — no close button."""

    def __init__(self, message: str = "", plan: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("License Expired")
        self.setFixedSize(420, 300)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint
            # No close button — must quit
        )
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)

        icon = QLabel("⏰")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("License Expired")
        title.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {COLORS['red']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        msg_lbl = QLabel(message or "Your license has expired.\nPlease renew to continue.")
        msg_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS['muted']};")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        quit_btn = QPushButton("Exit Application")
        quit_btn.setFixedHeight(44)
        quit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['red']}; border: none;
                border-radius: 10px; color: white;
                font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #FF6B6B; }}
        """)
        quit_btn.clicked.connect(lambda: sys.exit(0))
        layout.addWidget(quit_btn)
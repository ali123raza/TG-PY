"""
TG-PY Python Frontend
Modern Telegram Automation GUI built with PyQt6
"""
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QListWidget, QTabWidget, QGroupBox, QSplitter,
    QHBoxLayout, QStackedWidget, QPushButton, QLabel,
    QFrame, QScrollArea, QSizePolicy, QSpacerItem,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QDialog, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QSpinBox, QFileDialog,
    QMessageBox, QSplitter, QGridLayout, QGroupBox, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QUrl
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QBrush, QPixmap, QDesktopServices

# Import our modules
from models import Account, Proxy, Campaign, MessageTemplate, Log, Stats, Job, ScrapedMember, Settings
from data_service import get_data_service
from toast import init_toast_manager, toast_success, toast_error, toast_info, toast_warning
from contacts_page import ContactsPage
from templates_page import TemplatesPage, TemplateBuilderDialog

# FIX 1: SESSIONS_DIR was used in AccountsPage.load_sessions() but never imported → NameError crash
from core.config import SESSIONS_DIR

# Get data service (replaces API client)
data_service = get_data_service()
MEDIA_BASE_URL = ""  # No longer needed with direct file access

# Enhanced Color Palette with Gradients
COLORS = {
    # Base colors
    'bg_primary': '#0D1117',
    'bg_secondary': '#161B22',
    'bg_tertiary': '#21262D',
    'bg_hover': '#30363D',
    'bg_selected': '#1F6FEB',

    # Text colors
    'text_primary': '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted': '#6E7681',
    'text_inverse': '#0D1117',

    # Border
    'border': '#30363D',
    'border_light': '#21262D',

    # Accents
    'accent_blue': '#58A6FF',
    'accent_blue_dark': '#1F6FEB',
    'accent_green': '#3FB950',
    'accent_green_dark': '#238636',
    'accent_red': '#F85149',
    'accent_red_dark': '#DA3633',
    'accent_yellow': '#D29922',
    'accent_yellow_dark': '#9E6A03',
    'accent_purple': '#A371F7',
    'accent_pink': '#F778BA',
    'accent_cyan': '#39CFCF',

    # Gradients
    'gradient_blue':   'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #58A6FF, stop:1 #1F6FEB)',
    'gradient_green':  'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3FB950, stop:1 #238636)',
    'gradient_red':    'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F85149, stop:1 #DA3633)',
    'gradient_purple': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #A371F7, stop:1 #8957E5)',
    # FIX 2: gradient_yellow was missing → KeyError crash in CampaignsPage
    'gradient_yellow': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #D29922, stop:1 #9E6A03)',
    'gradient_card':   'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #21262D, stop:1 #161B22)',

    # Sidebar
    'sidebar_bg': '#0D1117',
}

# ── Action button hover gradients (used in all table action buttons) ──────────
BTN_BLUE   = "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD)"
BTN_GREEN  = "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #56D364,stop:1 #2EA043)"
BTN_RED    = "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149)"
BTN_YELLOW = "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FFD700,stop:1 #D29922)"
BTN_PURPLE = "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #A371F7,stop:1 #8957E5)"


class ModernStyle:
    @staticmethod
    def get_main_stylesheet():
        return f"""
            QMainWindow {{ background-color: {COLORS['bg_primary']}; }}
            QWidget {{ background-color: transparent; color: {COLORS['text_primary']};
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px; }}
            QLabel {{ color: {COLORS['text_primary']}; padding: 2px; }}
            QLabel[secondary="true"] {{ color: {COLORS['text_secondary']}; font-size: 12px; }}
            QPushButton {{ background-color: {COLORS['bg_tertiary']}; border: 1px solid {COLORS['border']};
                border-radius: 10px; padding: 10px 18px; color: {COLORS['text_primary']}; font-weight: 500; }}
            QPushButton:hover {{ background-color: {COLORS['bg_hover']}; border-color: {COLORS['accent_blue']}; }}
            QPushButton:pressed {{ background-color: {COLORS['bg_selected']}; }}
            QPushButton[primary="true"] {{ background: {COLORS['gradient_blue']}; border: none; color: white; font-weight: 600; }}
            QPushButton[primary="true"]:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD); }}
            QPushButton[success="true"] {{ background: {COLORS['gradient_green']}; border: none; color: white; font-weight: 600; }}
            QPushButton[success="true"]:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #56D364, stop:1 #2EA043); }}
            QPushButton[danger="true"] {{ background: {COLORS['gradient_red']}; border: none; color: white; font-weight: 600; }}
            QPushButton[danger="true"]:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7B72, stop:1 #F85149); }}
            QFrame[sidebar="true"] {{ background-color: {COLORS['sidebar_bg']}; border-right: 1px solid {COLORS['border']}; }}
            QFrame[card="true"] {{ background: {COLORS['gradient_card']}; border: 1px solid {COLORS['border']};
                border-radius: 14px; padding: 20px; }}
            QFrame[card="true"]:hover {{ border-color: {COLORS['accent_blue_dark']}; }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{ background-color: {COLORS['bg_primary']};
                border: 2px solid {COLORS['border']}; border-radius: 10px; padding: 10px 14px;
                color: {COLORS['text_primary']}; font-size: 13px; }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {COLORS['accent_blue']}; background-color: {COLORS['bg_secondary']}; }}
            QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover {{
                border-color: {COLORS['bg_hover']}; }}
            QTableWidget {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};
                border-radius: 14px; gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['bg_selected']}; }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {COLORS['border_light']}; }}
            QTableWidget::item:selected {{ background-color: rgba(31, 111, 235, 0.3); color: {COLORS['text_primary']}; }}
            QTableWidget::item:hover {{ background-color: {COLORS['bg_hover']}; }}
            QHeaderView::section {{ background-color: {COLORS['bg_tertiary']}; padding: 12px;
                border: none; font-weight: 600; color: {COLORS['text_secondary']}; }}
            QTabWidget::pane {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};
                border-radius: 14px; top: -1px; }}
            QTabBar::tab {{ background-color: {COLORS['bg_primary']}; border: 1px solid {COLORS['border']};
                padding: 12px 24px; margin-right: 6px; border-top-left-radius: 10px;
                border-top-right-radius: 10px; color: {COLORS['text_secondary']}; font-weight: 500; }}
            QTabBar::tab:selected {{ background-color: {COLORS['bg_secondary']};
                border-bottom-color: {COLORS['bg_secondary']}; color: {COLORS['accent_blue']}; }}
            QTabBar::tab:hover:!selected {{ background-color: {COLORS['bg_tertiary']}; color: {COLORS['text_primary']}; }}
            QListWidget {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};
                border-radius: 12px; padding: 6px; outline: none; }}
            QListWidget::item {{ padding: 10px 12px; border-radius: 8px; margin: 2px 0; }}
            QListWidget::item:selected {{ background-color: rgba(31, 111, 235, 0.2);
                border: 1px solid {COLORS['accent_blue_dark']}; }}
            QListWidget::item:hover {{ background-color: {COLORS['bg_hover']}; }}
            QGroupBox {{ color: {COLORS['text_secondary']}; font-weight: 600;
                border: 1px solid {COLORS['border']}; border-radius: 14px;
                margin-top: 12px; padding-top: 16px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 0 8px; color: {COLORS['accent_blue']}; }}
            QScrollBar:vertical {{ background-color: {COLORS['bg_primary']}; width: 10px; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background-color: {COLORS['bg_hover']}; border-radius: 5px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background-color: {COLORS['text_muted']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QProgressBar {{ background-color: {COLORS['bg_tertiary']}; border: none; border-radius: 8px;
                text-align: center; font-weight: 500; }}
            QProgressBar::chunk {{ background: {COLORS['gradient_green']}; border-radius: 8px; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent;
                border-right: 5px solid transparent; border-top: 5px solid {COLORS['text_secondary']};
                width: 0; height: 0; }}
            QComboBox QAbstractItemView {{ background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']}; border-radius: 10px;
                selection-background-color: {COLORS['bg_selected']}; }}
            QCheckBox {{ spacing: 8px; }}
            QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px;
                border: 2px solid {COLORS['border']}; background-color: {COLORS['bg_primary']}; }}
            QCheckBox::indicator:checked {{ background-color: {COLORS['accent_green']}; border-color: {COLORS['accent_green']}; }}
            QCheckBox::indicator:hover {{ border-color: {COLORS['accent_blue']}; }}
            QDialog {{ background-color: {COLORS['bg_primary']}; }}
            QMenu {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};
                border-radius: 10px; padding: 8px; }}
            QMenu::item {{ padding: 10px 20px; border-radius: 6px; }}
            QMenu::item:selected {{ background-color: {COLORS['bg_hover']}; }}
        """


class SidebarButton(QPushButton):
    def __init__(self, icon_text, label, parent=None):
        super().__init__(parent)
        self.icon_text = icon_text
        self.label_text = label
        self.setText(f"{icon_text}  {label}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: none; border-radius: 12px;
                padding: 12px 18px; color: {COLORS['text_secondary']}; font-size: 14px;
                font-weight: 500; text-align: left; }}
            QPushButton:hover {{ background-color: {COLORS['bg_tertiary']}; color: {COLORS['text_primary']}; }}
            QPushButton:checked {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(31,111,235,0.15), stop:1 rgba(31,111,235,0.05));
                border-left: 3px solid {COLORS['accent_blue']}; color: {COLORS['accent_blue']}; font-weight: 600; }}
        """)

    def set_active(self, active: bool):
        self.setChecked(active)


class Sidebar(QFrame):
    def __init__(self, navigate_callback, parent=None):
        super().__init__(parent)
        self.navigate_callback = navigate_callback
        self.buttons = {}
        self.init_ui()

    def init_ui(self):
        self.setProperty("sidebar", True)
        self.setFixedWidth(260)
        self.setStyleSheet(f"""
            QFrame[sidebar="true"] {{
                background-color: {COLORS['sidebar_bg']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(6)

        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel("📱")
        logo_icon.setStyleSheet("font-size: 28px;")
        logo_layout.addWidget(logo_icon)
        logo_text = QLabel("TG-PY")
        logo_text.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['accent_blue']}; padding-left: 8px;")
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        layout.addWidget(logo_container)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent, stop:0.5 {COLORS['border']}, stop:1 transparent);
            max-height: 1px;
        """)
        layout.addWidget(separator)
        layout.addSpacing(20)

        nav_items = [
            ("📊", "Dashboard",  "Dashboard"),
            ("👤", "Accounts",   "Accounts"),
            ("💬", "Messaging",  "Messaging"),
            ("🎯", "Campaigns",  "Campaigns"),
            ("🔍", "Scraper",    "Scraper"),
            ("🌐", "Proxies",    "Proxies"),
            ("📝", "Templates",  "Templates"),
            ("👥", "Contacts",   "Contacts"),
            ("📋", "Logs",       "Logs"),
            ("⚙️", "Settings",  "Settings"),
        ]
        for icon, label, page in nav_items:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, p=page: self.navigate_callback(p))
            self.buttons[page] = btn
            layout.addWidget(btn)

        layout.addStretch()

        version_container = QFrame()
        version_container.setStyleSheet(f"background-color: {COLORS['bg_tertiary']}; border-radius: 8px; padding: 8px;")
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(12, 8, 12, 8)
        version_layout.addWidget(QLabel("🔷"))
        version = QLabel("v1.0.0")
        version.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        version_layout.addWidget(version)
        version_layout.addStretch()
        layout.addWidget(version_container)


class StatCard(QFrame):
    def __init__(self, label, value, sub="", color=COLORS['text_primary'], icon="", parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        self.card_color = color
        self.setStyleSheet(f"""
            QFrame[card="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['bg_tertiary']}, stop:1 {COLORS['bg_secondary']});
                border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 4px;
            }}
            QFrame[card="true"]:hover {{ border-color: {color}; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        top_layout = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 24px;")
            top_layout.addWidget(icon_label)
        self.label = QLabel(label)
        self.label.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']}; font-weight: 500;")
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.value = QLabel(str(value))
        self.value.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        layout.addWidget(self.value)

        if sub:
            self.sub = QLabel(sub)
            self.sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']};")
            layout.addWidget(self.sub)

    def update_value(self, value, sub=None):
        self.value.setText(str(value))
        if sub and hasattr(self, 'sub'):
            self.sub.setText(sub)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.stats = None
        self.init_ui()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.fetch_stats)
        self.poll_timer.start(30000)   # 30s — stats don't need real-time

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        title_icon = QLabel("📊")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        title = QLabel("Dashboard")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        # ── License info badge ────────────────────────────────────────────────
        try:
            import builtins
            lic = getattr(builtins, 'TGPY_LICENSE', None)
            if lic:
                plan_text = lic.plan.upper() if lic.plan else "—"
                days_text = (f"{lic.days_remaining}d left"
                             if lic.days_remaining is not None else "♾ Lifetime")
                user_text = lic.username
                badge_color = '#3FB950' if (lic.days_remaining is None or lic.days_remaining > 7) else '#D29922'

                badge = QLabel(f"👤 {user_text}  ·  🔑 {plan_text}  ·  ⏱ {days_text}")
                badge.setStyleSheet(f"""
                    background: rgba(63,185,80,0.1);
                    border: 1px solid {badge_color};
                    border-radius: 20px;
                    padding: 6px 16px;
                    color: {badge_color};
                    font-size: 12px;
                    font-weight: 600;
                """)
                title_layout.addWidget(badge)
        except Exception:
            pass

        layout.addWidget(title_container)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        for i in range(4):
            stats_grid.setColumnStretch(i, 1)

        self.stat_cards = {
            'accounts':    StatCard("Accounts",      "—", "—", COLORS['accent_blue'],   "👥"),
            'messages':    StatCard("Messages Sent",  "—", "—", COLORS['accent_green'],  "✉️"),
            'success_rate':StatCard("Success Rate",   "—", "",  COLORS['accent_yellow'], "📈"),
            'campaigns':   StatCard("Campaigns",      "—", "—", COLORS['accent_purple'], "🎯"),
            'proxies':     StatCard("Proxies",        "—", "",  COLORS['accent_cyan'],   "🌐"),
            'templates':   StatCard("Templates",      "—", "",  COLORS['accent_pink'],   "📝"),
            'scrape_ops':  StatCard("Scrape Ops",     "—", "",  COLORS['accent_yellow'], "🔍"),
            'total':       StatCard("Total Messages", "—", "",  COLORS['text_secondary'],"📊"),
        }
        positions = [(0,0),(0,1),(0,2),(0,3),(1,0),(1,1),(1,2),(1,3)]
        for (row, col), (key, card) in zip(positions, self.stat_cards.items()):
            stats_grid.addWidget(card, row, col)
        layout.addLayout(stats_grid)

        bottom_layout = QHBoxLayout()
        self.accounts_group = QGroupBox("Per-Account Stats")
        self.accounts_group.setStyleSheet(f"""
            QGroupBox {{ color: {COLORS['text_secondary']}; font-weight: 600;
                border: 1px solid {COLORS['border']}; border-radius: 12px;
                margin-top: 12px; padding-top: 12px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 8px; color: {COLORS['accent_blue']}; }}
        """)
        accounts_layout = QVBoxLayout(self.accounts_group)
        accounts_layout.setSpacing(8)
        accounts_layout.setContentsMargins(12, 16, 12, 12)
        self.accounts_list = QListWidget()
        self.accounts_list.setStyleSheet(f"""
            QListWidget {{ background-color: {COLORS['bg_primary']}; border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px; }}
            QListWidget::item {{ padding: 8px 12px; border-radius: 6px; margin: 2px 0; }}
            QListWidget::item:hover {{ background-color: {COLORS['bg_hover']}; }}
        """)
        accounts_layout.addWidget(self.accounts_list)
        bottom_layout.addWidget(self.accounts_group, 1)

        self.logs_group = QGroupBox("Recent Activity")
        self.logs_group.setStyleSheet(self.accounts_group.styleSheet())
        logs_layout = QVBoxLayout(self.logs_group)
        logs_layout.setSpacing(8)
        logs_layout.setContentsMargins(12, 16, 12, 12)
        self.logs_list = QListWidget()
        self.logs_list.setStyleSheet(self.accounts_list.styleSheet())
        logs_layout.addWidget(self.logs_list)
        bottom_layout.addWidget(self.logs_group, 1)

        layout.addLayout(bottom_layout)
        layout.addStretch()
        self.fetch_stats()

    def fetch_stats(self):
        try:
            data = self.data.get_stats()
            self.stats = Stats.from_dict(data)
            self.update_display()
        except Exception as e:
            toast_error(f"Failed to fetch stats: {e}")

    def closeEvent(self, event):
        self.poll_timer.stop()
        event.accept()

    def update_display(self):
        if not self.stats:
            return
        acc = self.stats.accounts
        self.stat_cards['accounts'].update_value(acc.get('total', 0), f"{acc.get('active', 0)} active")
        msg = self.stats.messages
        self.stat_cards['messages'].update_value(msg.get('sent', 0), f"{msg.get('failed', 0)} failed")
        self.stat_cards['total'].update_value(msg.get('total', 0), "")
        self.stat_cards['success_rate'].update_value(self.stats.success_rate, "")
        camp = self.stats.campaigns
        status_str = ', '.join([f"{v} {k}" for k, v in camp.get('by_status', {}).items()]) or 'none'
        self.stat_cards['campaigns'].update_value(camp.get('total', 0), status_str)
        self.stat_cards['proxies'].update_value(self.stats.proxies, "")
        self.stat_cards['templates'].update_value(self.stats.templates, "")
        self.stat_cards['scrape_ops'].update_value(self.stats.scrape_ops, "")

        self.accounts_list.clear()
        for acc_stat in self.stats.per_account:
            name = acc_stat.get('name') or acc_stat.get('phone', 'Unknown')
            sent = acc_stat.get('sent', 0)
            failed = acc_stat.get('failed', 0)
            total = sent + failed
            pct = (sent / total * 100) if total > 0 else 0
            self.accounts_list.addItem(QListWidgetItem(f"{name}: {sent} sent, {failed} failed ({pct:.0f}%)"))
        if not self.stats.per_account:
            self.accounts_list.addItem("No messaging activity yet")

        self.logs_list.clear()
        for log in self.stats.recent_logs[:20]:
            time_str = log.get('created_at', '').split('T')[1][:8] if 'T' in log.get('created_at', '') else ''
            msg = f"[{time_str}] [{log.get('category', 'general')}] {log.get('message', '')}"
            item = QListWidgetItem(msg)
            level = log.get('level', 'info')
            if level == 'error':
                item.setForeground(QColor(COLORS['accent_red']))
            elif level == 'warn':
                item.setForeground(QColor(COLORS['accent_yellow']))
            else:
                item.setForeground(QColor(COLORS['text_secondary']))
            self.logs_list.addItem(item)
        if not self.stats.recent_logs:
            self.logs_list.addItem("No recent activity")


class AccountsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.accounts: list[Account] = []
        self.proxies: list[Proxy] = []
        self.selected_accounts: set[int] = set()
        self.load_polling = False
        self.import_polling = False
        self.init_ui()
        self.fetch_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title_icon = QLabel("👤")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        title = QLabel("Accounts")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        header.addWidget(title)
        header.addStretch()

        self.load_sessions_btn = QPushButton("Load Sessions")
        self.load_sessions_btn.clicked.connect(self.load_sessions)
        header.addWidget(self.load_sessions_btn)

        self.import_tdata_btn = QPushButton("Import tdata")
        self.import_tdata_btn.clicked.connect(self.import_tdata)
        header.addWidget(self.import_tdata_btn)

        self.check_all_btn = QPushButton("Check All Health")
        self.check_all_btn.clicked.connect(self.check_all_health)
        header.addWidget(self.check_all_btn)

        self.delete_selected_btn = QPushButton("Delete Selected")
        self.delete_selected_btn.setProperty("danger", True)
        self.delete_selected_btn.clicked.connect(self.delete_selected)
        header.addWidget(self.delete_selected_btn)

        self.add_account_btn = QPushButton("+ Add Account")
        self.add_account_btn.setProperty("primary", True)
        self.add_account_btn.clicked.connect(self.show_add_dialog)
        header.addWidget(self.add_account_btn)
        layout.addLayout(header)

        self.status_frame = QFrame()
        self.status_frame.setVisible(False)
        status_layout = QHBoxLayout(self.status_frame)
        self.status_label = QLabel("")
        status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        status_layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Select", "Phone", "Name", "Username", "Status", "Messages", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 90)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 90)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 210)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};
                border-radius: 12px; gridline-color: {COLORS['border_light']}; }}
            QTableWidget::item {{ padding: 6px 10px; border-bottom: 1px solid {COLORS['border_light']}; }}
            QTableWidget::item:selected {{ background-color: rgba(31,111,235,0.2); color: {COLORS['text_primary']}; }}
            QHeaderView::section {{ background-color: {COLORS['bg_tertiary']}; padding: 10px 8px;
                border: none; font-weight: 600; color: {COLORS['text_secondary']}; }}
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.table)

    def fetch_data(self):
        try:
            self.accounts = [Account.from_dict(a) for a in self.data.get_accounts()]
            self.proxies  = [Proxy.from_dict(p)   for p in self.data.get_proxies()]
            self.update_table()
        except Exception as e:
            toast_error(f"Failed to fetch data: {e}")

    def update_table(self):
        # Filter out any empty/invalid accounts (no phone = ghost row)
        valid_accounts = [a for a in self.accounts if a.phone and a.phone.strip()]
        self.table.setRowCount(len(valid_accounts))
        for row, account in enumerate(valid_accounts):
            cb = QCheckBox()
            cb.setChecked(account.id in self.selected_accounts)
            cb.stateChanged.connect(lambda state, aid=account.id: self.toggle_selection(aid, state))
            self.table.setCellWidget(row, 0, cb)
            self.table.setItem(row, 1, QTableWidgetItem(account.phone))
            self.table.setItem(row, 2, QTableWidgetItem(account.name))
            self.table.setItem(row, 3, QTableWidgetItem(account.username))

            status_item = QTableWidgetItem(account.status)
            if account.status == "active":
                status_item.setForeground(QColor(COLORS['accent_green']))
            elif account.status in ("banned", "restricted"):
                status_item.setForeground(QColor(COLORS['accent_red']))
            else:
                status_item.setForeground(QColor(COLORS['accent_yellow']))
            self.table.setItem(row, 4, status_item)
            self.table.setItem(row, 5, QTableWidgetItem(str(account.messages_sent)))

            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            al = QHBoxLayout(actions_widget)
            al.setContentsMargins(6, 4, 6, 4)
            al.setSpacing(5)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Check button
            check_btn = QPushButton("✓ Check")
            check_btn.setFixedHeight(30)
            check_btn.setMinimumWidth(72)
            check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            check_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #58A6FF,stop:1 #1F6FEB);
                    border: none; border-radius: 6px;
                    color: white; font-weight: 600; font-size: 11px; padding: 0px 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD);
                }
            """)
            check_btn.clicked.connect(lambda _, a=account: self.check_health(a))
            al.addWidget(check_btn)

            # Edit button
            edit_btn = QPushButton("✏ Edit")
            edit_btn.setFixedHeight(30)
            edit_btn.setMinimumWidth(62)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3FB950,stop:1 #238636);
                    border: none; border-radius: 6px;
                    color: white; font-weight: 600; font-size: 11px; padding: 0px 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #56D364,stop:1 #2EA043);
                }
            """)
            edit_btn.clicked.connect(lambda _, a=account: self.edit_account(a))
            al.addWidget(edit_btn)

            # Delete button
            del_btn = QPushButton("✕ Del")
            del_btn.setFixedHeight(30)
            del_btn.setMinimumWidth(56)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F85149,stop:1 #DA3633);
                    border: none; border-radius: 6px;
                    color: white; font-weight: 600; font-size: 11px; padding: 0px 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149);
                }
            """)
            del_btn.clicked.connect(lambda _, a=account: self.delete_account(a))
            al.addWidget(del_btn)

            self.table.setCellWidget(row, 6, actions_widget)
            self.table.setRowHeight(row, 44)

    def toggle_selection(self, account_id: int, state: int):
        if state == Qt.CheckState.Checked.value:
            self.selected_accounts.add(account_id)
        else:
            self.selected_accounts.discard(account_id)

    def edit_account(self, account: Account):
        """Edit account — change name, proxy, active status."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Account — {account.phone}")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_secondary']}; }}
            QLabel {{ color: {COLORS['text_primary']}; font-size: 13px; }}
            QLineEdit, QComboBox, QCheckBox {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border-color: {COLORS['accent_blue']}; }}
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
                background: {COLORS['gradient_blue']};
                border: none;
                color: white;
                font-weight: 600;
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header_label = QLabel(f"✏️  Editing: {account.phone}")
        header_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent_blue']}; margin-bottom: 4px;")
        layout.addWidget(header_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(sep)

        # Name
        layout.addWidget(QLabel("Display Name:"))
        name_input = QLineEdit(account.name)
        name_input.setPlaceholderText("Account display name")
        layout.addWidget(name_input)

        # Proxy
        layout.addWidget(QLabel("Assign Proxy:"))
        proxy_combo = QComboBox()
        proxy_combo.setStyleSheet(f"""
            QComboBox {{ background-color: {COLORS['bg_primary']}; border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 12px; color: {COLORS['text_primary']}; }}
            QComboBox:focus {{ border-color: {COLORS['accent_blue']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['accent_blue_dark']};
            }}
        """)
        proxy_combo.addItem("🚫  No Proxy (Direct)", None)
        current_proxy_idx = 0
        for i, proxy in enumerate(self.proxies):
            label = f"{proxy.scheme.upper()}  {proxy.host}:{proxy.port}"
            if proxy.username:
                label += f"  ({proxy.username})"
            proxy_combo.addItem(label, proxy.id)
            if proxy.id == account.proxy_id:
                current_proxy_idx = i + 1   # +1 because of "No Proxy" at index 0
        proxy_combo.setCurrentIndex(current_proxy_idx)
        layout.addWidget(proxy_combo)

        # Current proxy info box
        if account.proxy_id:
            cur_proxy = next((p for p in self.proxies if p.id == account.proxy_id), None)
            if cur_proxy:
                info_frame = QFrame()
                info_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['bg_primary']};
                        border: 1px solid {COLORS['border_light']};
                        border-radius: 6px;
                        padding: 6px;
                    }}
                """)
                info_layout = QHBoxLayout(info_frame)
                info_layout.setContentsMargins(10, 6, 10, 6)
                info_lbl = QLabel(f"Current: {cur_proxy.scheme}://{cur_proxy.host}:{cur_proxy.port}")
                info_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
                info_layout.addWidget(info_lbl)
                layout.addWidget(info_frame)
        else:
            info_lbl = QLabel("Current: No proxy assigned")
            info_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
            layout.addWidget(info_lbl)

        # Active toggle
        active_check = QCheckBox("Account is Active")
        active_check.setChecked(account.is_active)
        active_check.setStyleSheet(f"""
            QCheckBox {{ color: {COLORS['text_primary']}; font-size: 13px; spacing: 8px; }}
            QCheckBox::indicator {{
                width: 20px; height: 20px; border-radius: 6px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_primary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent_green']};
                border-color: {COLORS['accent_green']};
            }}
        """)
        layout.addWidget(active_check)

        layout.addSpacing(8)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primary")

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def save():
            new_name     = name_input.text().strip()
            new_proxy_id = proxy_combo.currentData()
            new_active   = active_check.isChecked()

            if not new_name:
                name_input.setStyleSheet(name_input.styleSheet() + "border-color: red;")
                return

            try:
                self.data.update_account(account.id, {
                    "name":      new_name,
                    "proxy_id":  new_proxy_id,
                    "is_active": new_active,
                })

                # Friendly confirmation message
                proxy_msg = "no proxy"
                if new_proxy_id:
                    p = next((p for p in self.proxies if p.id == new_proxy_id), None)
                    if p:
                        proxy_msg = f"{p.host}:{p.port}"

                toast_success(f"Account updated — proxy: {proxy_msg}")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to update: {e}")

        save_btn.clicked.connect(save)
        dialog.exec()

    def show_add_dialog(self):
        from login_dialog import LoginDialog
        dialog = LoginDialog(self, proxies=self.proxies)
        dialog.account_added.connect(self.fetch_data)
        dialog.exec()

    def check_health(self, account: Account):
        try:
            response = self.data.check_account_health(account.id)
            toast_info(f"Account {account.phone}: {response.get('status', 'unknown')}")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Health check failed: {e}")

    def check_all_health(self):
        try:
            self.data.check_all_accounts_health()
            toast_info("Health check started for all accounts")
            QTimer.singleShot(3000, self.fetch_data)
        except Exception as e:
            toast_error(f"Failed to start health check: {e}")

    def delete_account(self, account: Account):
        reply = QMessageBox.question(self, "Delete Account", f"Delete account {account.phone}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_account(account.id)
                toast_success("Account deleted")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to delete: {e}")

    def delete_selected(self):
        if not self.selected_accounts:
            toast_warning("No accounts selected")
            return
        reply = QMessageBox.question(self, "Delete Accounts", f"Delete {len(self.selected_accounts)} accounts?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            deleted = 0
            for account_id in list(self.selected_accounts):
                try:
                    self.data.delete_account(account_id)
                    deleted += 1
                except Exception as e:
                    toast_error(f"Failed to delete account {account_id}: {e}")
            toast_success(f"Deleted {deleted} accounts")
            self.selected_accounts.clear()
            self.fetch_data()

    def load_sessions(self):
        try:
            # SESSIONS_DIR now properly imported at top of file (FIX 1)
            job_id = self.data.load_sessions_from_folder(str(SESSIONS_DIR))
            if not job_id:
                toast_info("No sessions to load")
                return
            self.status_frame.setVisible(True)
            self.status_label.setText("Loading sessions...")
            self.progress_bar.setRange(0, 0)
            self.load_polling = True
            self.poll_load_status(job_id)
        except Exception as e:
            toast_error(f"Failed to load sessions: {e}")

    def poll_load_status(self, job_id: str):
        if not self.load_polling:
            return
        try:
            status = self.data.get_job_status(job_id)
            total     = status.get("total", 0)
            completed = status.get("progress", 0)
            self.status_label.setText(f"Loading sessions: {completed}/{total}")
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(completed)
            if status.get("status") == "completed":
                self.load_polling = False
                self.status_frame.setVisible(False)
                toast_success(f"Loaded {completed} sessions")
                self.fetch_data()
            else:
                QTimer.singleShot(2000, lambda: self.poll_load_status(job_id))
        except Exception as e:
            self.load_polling = False
            self.status_frame.setVisible(False)
            toast_error(f"Load status check failed: {e}")

    def import_tdata(self):
        reply = QMessageBox.question(self, "Import tdata",
                                     "Import accounts from tgdata folder?\nThis will assign proxies round-robin.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from core.config import TGDATA_DIR
            job_id = self.data.import_tdata(str(TGDATA_DIR))
            if not job_id:
                toast_info("No tdata folders found")
                return
            self.status_frame.setVisible(True)
            self.status_label.setText("Importing tdata...")
            self.progress_bar.setRange(0, 0)
            self.import_polling = True
            self.poll_import_status(job_id)
        except Exception as e:
            toast_error(f"Failed to start import: {e}")

    def poll_import_status(self, job_id: str):
        if not self.import_polling:
            return
        try:
            status   = self.data.get_job_status(job_id)
            total    = status.get("total", 0)
            imported = status.get("progress", 0)
            self.status_label.setText(f"Importing: {imported}/{total}")
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(imported)
            job_status = status.get("status")
            if job_status in ("completed", "failed"):
                self.import_polling = False
                self.status_frame.setVisible(False)
                if job_status == "completed":
                    toast_success(f"Imported {imported} accounts")
                else:
                    toast_error(f"Import failed: {status.get('message', 'Unknown error')}")
                self.fetch_data()
            else:
                QTimer.singleShot(2000, lambda: self.poll_import_status(job_id))
        except Exception as e:
            self.import_polling = False
            self.status_frame.setVisible(False)
            toast_error(f"Import status check failed: {e}")


class MessagingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.accounts = []
        self.templates = []
        self.current_job = ""
        self.selected_accounts = set()
        self.account_buttons = {}
        # FIX 3: removed self.job_poller — JobPoller was never imported → NameError
        self._job_timer: QTimer | None = None
        self.init_ui()
        self.fetch_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        title_icon = QLabel("💬")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        title = QLabel("Messaging")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addWidget(title_container)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)

        accounts_group = QGroupBox("Select Accounts")
        accounts_layout = QVBoxLayout(accounts_group)
        self.accounts_container = QWidget()
        self.accounts_flow = QHBoxLayout(self.accounts_container)
        self.accounts_flow.setSpacing(8)
        self.accounts_flow.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.accounts_flow.addStretch()
        accounts_layout.addWidget(self.accounts_container)
        self.no_accounts_label = QLabel("No accounts. Add one first.")
        self.no_accounts_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        self.no_accounts_label.setVisible(False)
        accounts_layout.addWidget(self.no_accounts_label)
        left_layout.addWidget(accounts_group)

        targets_group = QGroupBox("Targets")
        targets_layout = QVBoxLayout(targets_group)

        # Mode toggle — Custom Input or Peer
        mode_row = QHBoxLayout()
        self.targets_mode_custom = QPushButton("✏ Custom Input")
        self.targets_mode_peer   = QPushButton("👥 Select Peer")
        for tbtn in (self.targets_mode_custom, self.targets_mode_peer):
            tbtn.setCheckable(True)
            tbtn.setFixedHeight(28)
            tbtn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px; padding: 0 12px;
                    color: {COLORS['text_secondary']}; font-size: 12px;
                }}
                QPushButton:checked {{
                    background: {COLORS['accent_blue_dark']};
                    border-color: {COLORS['accent_blue']};
                    color: white; font-weight: 600;
                }}
                QPushButton:hover:!checked {{ background: {COLORS['bg_hover']}; }}
            """)
        self.targets_mode_custom.setChecked(True)
        self.targets_mode_custom.clicked.connect(lambda: self._set_targets_mode("custom"))
        self.targets_mode_peer.clicked.connect(lambda: self._set_targets_mode("peer"))
        mode_row.addWidget(self.targets_mode_custom)
        mode_row.addWidget(self.targets_mode_peer)
        mode_row.addStretch()
        targets_layout.addLayout(mode_row)

        # Custom input widget
        self.custom_targets_widget = QWidget()
        ctl = QVBoxLayout(self.custom_targets_widget)
        ctl.setContentsMargins(0, 4, 0, 0)
        self.targets_input = QTextEdit()
        self.targets_input.setPlaceholderText("@username\n+923001234567\nuser_id")
        self.targets_input.setMaximumHeight(120)
        ctl.addWidget(self.targets_input)
        targets_layout.addWidget(self.custom_targets_widget)

        # Peer selector widget
        self.peer_targets_widget = QWidget()
        ptl = QVBoxLayout(self.peer_targets_widget)
        ptl.setContentsMargins(0, 4, 0, 0)
        self.peer_selector_combo = QComboBox()
        self.peer_selector_combo.addItem("— Select a peer —", None)
        ptl.addWidget(self.peer_selector_combo)
        self.peer_count_lbl = QLabel("")
        self.peer_count_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        ptl.addWidget(self.peer_count_lbl)
        self.peer_targets_widget.setVisible(False)
        targets_layout.addWidget(self.peer_targets_widget)

        left_layout.addWidget(targets_group)

        template_group = QGroupBox("Message Template (optional)")
        template_layout = QVBoxLayout(template_group)
        self.template_combo = QComboBox()
        self.template_combo.addItem("None (use custom message)", None)
        template_layout.addWidget(self.template_combo)
        left_layout.addWidget(template_group)

        message_group = QGroupBox("Message")
        message_layout = QVBoxLayout(message_group)
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Enter your message here...")
        message_layout.addWidget(self.message_input)
        left_layout.addWidget(message_group)

        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Delay Min (s):"))
        self.delay_min = QSpinBox()
        self.delay_min.setRange(1, 3600)
        self.delay_min.setValue(5)
        settings_layout.addWidget(self.delay_min)
        settings_layout.addWidget(QLabel("Delay Max (s):"))
        self.delay_max = QSpinBox()
        self.delay_max.setRange(1, 3600)
        self.delay_max.setValue(15)
        settings_layout.addWidget(self.delay_max)
        settings_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["sequential", "round_robin", "random"])
        settings_layout.addWidget(self.mode_combo)
        settings_layout.addStretch()
        left_layout.addLayout(settings_layout)

        self.send_btn = QPushButton("Send Messages")
        self.send_btn.setProperty("primary", True)
        self.send_btn.clicked.connect(self.send_messages)
        left_layout.addWidget(self.send_btn)
        left_layout.addStretch()
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        progress_group = QGroupBox("Job Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.job_status = QLabel("No active job")
        progress_layout.addWidget(self.job_status)
        self.job_progress = QProgressBar()
        progress_layout.addWidget(self.job_progress)
        right_layout.addWidget(progress_group)

        logs_group = QGroupBox("Recent Activity")
        logs_layout = QVBoxLayout(logs_group)
        self.logs_list = QListWidget()
        logs_layout.addWidget(self.logs_list)
        right_layout.addWidget(logs_group)
        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

    def _set_targets_mode(self, mode: str):
        self.targets_mode_custom.setChecked(mode == "custom")
        self.targets_mode_peer.setChecked(mode == "peer")
        self.custom_targets_widget.setVisible(mode == "custom")
        self.peer_targets_widget.setVisible(mode == "peer")
        if mode == "peer":
            self._refresh_peer_selector()

    def _refresh_peer_selector(self):
        try:
            peers = self.data.get_peers()
            self.peer_selector_combo.clear()
            self.peer_selector_combo.addItem("— Select a peer —", None)
            for p in peers:
                self.peer_selector_combo.addItem(
                    f"● {p['title']}  ({p.get('contact_count', 0):,} contacts)",
                    p["id"])
            self.peer_selector_combo.currentIndexChanged.connect(
                self._on_peer_selected)
        except Exception as e:
            toast_error(f"Could not load peers: {e}")

    def _on_peer_selected(self):
        peer_id = self.peer_selector_combo.currentData()
        if peer_id:
            try:
                counts = self.data.get_peer_contact_count(peer_id)
                total = counts.get("total", 0)
                pending = counts.get("pending", 0)
                self.peer_count_lbl.setText(
                    f"{total:,} contacts  |  {pending:,} pending")
            except Exception:
                self.peer_count_lbl.setText("")
        else:
            self.peer_count_lbl.setText("")

    def fetch_data(self):
        try:
            self.accounts = [Account.from_dict(a) for a in self.data.get_accounts()]
            self.update_accounts_display()
            templates_data = self.data.get_templates()
            self.templates = [MessageTemplate.from_dict(t) for t in templates_data]
            self.template_combo.clear()
            self.template_combo.addItem("None (use custom message)", None)
            for template in self.templates:
                label = template.name
                if template.id:  # add variant indicator if available
                    self.template_combo.addItem(label, template.id)
                else:
                    self.template_combo.addItem(label, template.id)
            self.fetch_logs()
        except Exception as e:
            toast_error(f"Failed to fetch data: {e}")

    def update_accounts_display(self):
        for btn in self.account_buttons.values():
            btn.deleteLater()
        self.account_buttons.clear()
        while self.accounts_flow.count() > 1:
            item = self.accounts_flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.accounts:
            self.no_accounts_label.setVisible(True)
            return
        self.no_accounts_label.setVisible(False)
        for account in self.accounts:
            btn = QPushButton(f"{account.name or account.phone}")
            btn.setCheckable(True)
            btn.setChecked(account.id in self.selected_accounts)
            self._update_account_button_style(btn, account.id in self.selected_accounts)
            btn.clicked.connect(lambda checked, b=btn, aid=account.id: self.toggle_account(b, aid))
            self.account_buttons[account.id] = btn
            self.accounts_flow.insertWidget(self.accounts_flow.count() - 1, btn)

    def _update_account_button_style(self, btn, selected):
        if selected:
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {COLORS['accent_blue']}; border: 1px solid {COLORS['accent_blue']};
                    border-radius: 8px; padding: 8px 16px; color: white; font-weight: 500; }}
                QPushButton:hover {{ background-color: {COLORS['accent_blue_dark']}; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {COLORS['bg_tertiary']}; border: 1px solid {COLORS['border']};
                    border-radius: 8px; padding: 8px 16px; color: {COLORS['text_secondary']}; }}
                QPushButton:hover {{ background-color: {COLORS['bg_hover']}; border-color: {COLORS['accent_blue_dark']}; }}
            """)

    def toggle_account(self, btn, account_id):
        if account_id in self.selected_accounts:
            self.selected_accounts.discard(account_id)
            btn.setChecked(False)
            self._update_account_button_style(btn, False)
        else:
            self.selected_accounts.add(account_id)
            btn.setChecked(True)
            self._update_account_button_style(btn, True)

    def fetch_logs(self):
        try:
            logs = self.data.get_logs("messaging", 50)
            self.logs_list.clear()
            for log in logs:
                time_str = log.get('created_at', '').split('T')[1][:8] if 'T' in log.get('created_at', '') else '?'
                self.logs_list.addItem(QListWidgetItem(f"[{time_str}] {log.get('message', '')}"))
        except Exception as _log_err:
            print(f"MessagingPage fetch_logs error: {_log_err}")

    def send_messages(self):
        if not self.selected_accounts:
            toast_warning("Please select at least one account")
            return

        targets_text = self.targets_input.toPlainText().strip()
        if not targets_text:
            toast_warning("Please enter at least one target")
            return

        # Parse targets — skip blank lines
        targets = [t.strip() for t in targets_text.split("\n") if t.strip()]

        # Override with peer targets if peer mode is active
        if self.targets_mode_peer.isChecked():
            peer_id = self.peer_selector_combo.currentData()
            if not peer_id:
                toast_warning("Please select a peer")
                return
            try:
                targets = self.data.get_peer_targets(peer_id)
                if not targets:
                    toast_warning("Selected peer has no contacts")
                    return
                toast_info(f"Using peer: {len(targets):,} contacts")
            except Exception as e:
                toast_error(f"Could not load peer contacts: {e}")
                return

        # Check message
        msg_text    = self.message_input.toPlainText().strip()
        template_id = self.template_combo.currentData()
        if not msg_text and not template_id:
            toast_warning("Please enter a message or select a template")
            return

        # Classify targets for info toast
        usernames = [t for t in targets if t.startswith("@")]
        phones    = [t for t in targets if t.startswith("+") or t.lstrip("+").isdigit()]
        user_ids  = [t for t in targets if t.isdigit()]
        unknown   = [t for t in targets if t not in usernames + phones + user_ids]

        if unknown:
            toast_warning(
                f"{len(unknown)} target(s) have unknown format — "
                "use @username, +phone, or numeric user_id"
            )
            return

        # Phones require contact import — just inform user, we handle it automatically
        if phones:
            toast_info(
                f"{len(phones)} phone number(s) — "
                "will auto-import as contact to resolve"
            )

        data = {
            "account_ids": list(self.selected_accounts),
            "targets":     targets,
            "message":     msg_text,
            "template_id": template_id,
            "delay_min":   self.delay_min.value(),
            "delay_max":   self.delay_max.value(),
            "mode":        self.mode_combo.currentText(),
        }
        try:
            response = self.data.send_messages(data)
            self.current_job = response.get("job_id")
            if self.current_job:
                toast_success(
                    f"Started — {len(targets)} target(s), "
                    f"{len(list(self.selected_accounts))} account(s)"
                )
                self.start_job_polling()
            else:
                toast_error("Failed to start job")
        except Exception as e:
            toast_error(f"Failed to send: {e}")

    # FIX 3: replaced JobPoller (never imported → NameError) with QTimer polling
    def start_job_polling(self):
        if self._job_timer:
            self._job_timer.stop()
        self._job_timer = QTimer(self)
        self._job_timer.timeout.connect(self._poll_job)
        self._job_timer.start(2000)

    def _poll_job(self):
        if not self.current_job:
            return
        try:
            data = self.data.get_job_status(self.current_job)
            if data is None:
                return
            self.on_job_update(data)
            if data.get("status", "") in ("completed", "failed", "cancelled"):
                self._job_timer.stop()
                self.on_job_complete(data)
        except Exception as exc:
            print(f"Job poll error: {exc}")

    def on_job_update(self, data: dict):
        status  = data.get("status", "unknown")
        sent    = data.get("sent", 0)
        failed  = data.get("failed", 0)
        total   = data.get("total", 0)
        msg     = data.get("message", "")
        status_text = f"Status: {status} | Sent: {sent} | Failed: {failed}"
        if msg:
            status_text += f" | {msg}"
        self.job_status.setText(status_text)
        if total > 0:
            self.job_progress.setRange(0, total)
            self.job_progress.setValue(sent + failed)

    def on_job_complete(self, data: dict):
        status  = data.get("status", "unknown")
        sent    = data.get("sent", 0)
        failed  = data.get("failed", 0)
        msg     = data.get("message", "")
        if status == "completed":
            if failed > 0:
                toast_warning(f"Done — Sent: {sent}, Failed: {failed}")
            else:
                toast_success(f"Done — All {sent} messages sent!")
        elif status == "failed":
            # Show exact error message from job
            toast_error(f"Failed: {msg or 'Unknown error — check Logs page'}")
            self.job_status.setText(f"Error: {msg}")
        elif status == "cancelled":
            toast_info(f"Cancelled — Sent: {sent}, Failed: {failed}")
        else:
            toast_info(f"Job {status}")
        if status != "failed":
            self.job_status.setText("No active job")
        self.job_progress.setValue(0)
        self.fetch_data()
        self.fetch_logs()

    def closeEvent(self, event):
        if self._job_timer:
            self._job_timer.stop()
        event.accept()


class CampaignsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.campaigns = []
        self.init_ui()
        self.fetch_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        header = QHBoxLayout()
        title_icon = QLabel("🎯")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        title = QLabel("Campaigns")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        header.addWidget(title)
        header.addStretch()
        self.create_btn = QPushButton("+ Create Campaign")
        self.create_btn.setProperty("primary", True)
        self.create_btn.clicked.connect(self.create_campaign)
        header.addWidget(self.create_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Accounts", "Targets", "Delay", "Progress", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1,90),(2,75),(3,75),(4,90),(5,100),(6,220)]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};
                border-radius: 12px; gridline-color: {COLORS['border_light']}; }}
            QTableWidget::item {{ padding: 8px 12px; border-bottom: 1px solid {COLORS['border_light']}; }}
            QTableWidget::item:selected {{ background-color: rgba(31,111,235,0.2); color: {COLORS['text_primary']}; }}
            QHeaderView::section {{ background-color: {COLORS['bg_tertiary']}; padding: 12px;
                border: none; font-weight: 600; color: {COLORS['text_secondary']}; }}
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def fetch_data(self):
        try:
            self.campaigns = [Campaign.from_dict(c) for c in self.data.get_campaigns()]
            self.update_table()
        except Exception as e:
            toast_error(f"Failed to fetch campaigns: {e}")

    def update_table(self):
        self.table.setRowCount(len(self.campaigns))
        for row, campaign in enumerate(self.campaigns):
            self.table.setItem(row, 0, QTableWidgetItem(campaign.name))
            status_item = QTableWidgetItem(campaign.status)
            if campaign.status == "running":
                status_item.setForeground(QColor(COLORS['accent_green']))
            elif campaign.status == "completed":
                status_item.setForeground(QColor(COLORS['accent_blue']))
            elif campaign.status == "draft":
                status_item.setForeground(QColor(COLORS['accent_yellow']))
            self.table.setItem(row, 1, status_item)
            self.table.setItem(row, 2, QTableWidgetItem(str(len(campaign.account_ids))))
            self.table.setItem(row, 3, QTableWidgetItem(str(len(campaign.targets))))
            self.table.setItem(row, 4, QTableWidgetItem(f"{campaign.delay_min}-{campaign.delay_max}s"))
            self.table.setItem(row, 5, QTableWidgetItem(f"Retry: {campaign.retry_count}/{campaign.max_retries}"))

            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            al = QHBoxLayout(actions_widget)
            al.setContentsMargins(6, 4, 6, 4)
            al.setSpacing(5)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status = campaign.status

            def _make_btn(label, bg_start, bg_end, hov_start, hov_end, slot):
                b = QPushButton(label)
                b.setFixedHeight(30)
                b.setMinimumWidth(60)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(
                    f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                    f"stop:0 {bg_start},stop:1 {bg_end}); border: none; border-radius: 6px;"
                    f"color: white; font-weight: 600; font-size: 11px; padding: 0px 8px; }}"
                    f"QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                    f"stop:0 {hov_start},stop:1 {hov_end}); }}"
                )
                b.clicked.connect(slot)
                al.addWidget(b)

            if status == 'draft':
                _make_btn("▶ Run",   "#3FB950","#238636","#56D364","#2EA043", lambda _, c=campaign: self.run_campaign(c))
            elif status in ('running', 'scheduled'):
                _make_btn("⏸ Pause", "#D29922","#9E6A03","#FFD700","#D29922", lambda _, c=campaign: self.pause_campaign(c))
            elif status in ('completed', 'failed', 'paused'):
                _make_btn("↺ Rerun", "#58A6FF","#1F6FEB","#79B8FF","#388BFD", lambda _, c=campaign: self.rerun_campaign(c))

            _make_btn("✏ Edit", "#58A6FF","#1F6FEB","#79B8FF","#388BFD", lambda _, c=campaign: self.edit_campaign(c))
            _make_btn("✕ Del",  "#F85149","#DA3633","#FF7B72","#F85149", lambda _, c=campaign: self.delete_campaign(c))

            self.table.setCellWidget(row, 6, actions_widget)
            self.table.setRowHeight(row, 44)

    def create_campaign(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Campaign")
        dialog.setMinimumSize(540, 660)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {COLORS['bg_secondary']}; }}
            QLabel {{ color: {COLORS['text_primary']}; font-size: 13px; }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px;
                color: {COLORS['text_primary']};
            }}
            QListWidget {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 16px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(scroll_widget)
        form_layout.setSpacing(10)

        # ── Name ──────────────────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Campaign Name *"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g. Pakistan Leads Nov")
        form_layout.addWidget(name_input)

        # ── Accounts ──────────────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Select Accounts (Ctrl+Click for multiple)"))
        accounts_list = QListWidget()
        accounts_list.setMaximumHeight(110)
        accounts_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        try:
            for acc in self.data.get_accounts():
                item = QListWidgetItem(f"{acc.get('name') or acc.get('phone')} ({acc.get('status')})")
                item.setData(Qt.ItemDataRole.UserRole, acc.get('id'))
                accounts_list.addItem(item)
        except Exception:
            pass
        form_layout.addWidget(accounts_list)

        # ── Targets — Peer OR Custom ──────────────────────────────────────────
        targets_header = QHBoxLayout()
        targets_header.addWidget(QLabel("Targets"))
        use_peer_btn   = QPushButton("👥 Use Peer")
        use_custom_btn = QPushButton("✏ Custom Input")
        use_peer_btn.setCheckable(True)
        use_custom_btn.setCheckable(True)
        use_custom_btn.setChecked(True)
        for tbtn in (use_peer_btn, use_custom_btn):
            tbtn.setFixedHeight(26)
            tbtn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 5px; padding: 0 10px;
                    color: {COLORS['text_secondary']}; font-size: 12px;
                }}
                QPushButton:checked {{
                    background: {COLORS['accent_blue_dark']};
                    border-color: {COLORS['accent_blue']};
                    color: white; font-weight: 600;
                }}
                QPushButton:hover:!checked {{ background: {COLORS['bg_hover']}; }}
            """)
        targets_header.addWidget(use_custom_btn)
        targets_header.addWidget(use_peer_btn)
        targets_header.addStretch()
        form_layout.addLayout(targets_header)

        # Custom input
        custom_widget = QWidget()
        custom_widget.setStyleSheet("background: transparent;")
        cwl = QVBoxLayout(custom_widget)
        cwl.setContentsMargins(0, 0, 0, 0)
        targets_input = QTextEdit()
        targets_input.setMaximumHeight(90)
        targets_input.setPlaceholderText("+923001234567\n@username\nuser_id")
        cwl.addWidget(targets_input)
        form_layout.addWidget(custom_widget)

        # Peer selector
        peer_widget = QWidget()
        peer_widget.setStyleSheet("background: transparent;")
        pwl = QVBoxLayout(peer_widget)
        pwl.setContentsMargins(0, 0, 0, 0)
        peer_combo = QComboBox()
        peer_combo.addItem("— Select a peer —", None)
        peer_count_lbl = QLabel("")
        peer_count_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        try:
            for p in self.data.get_peers():
                peer_combo.addItem(
                    f"● {p['title']}  ({p.get('contact_count', 0):,} contacts)",
                    p["id"])
        except Exception:
            pass
        pwl.addWidget(peer_combo)
        pwl.addWidget(peer_count_lbl)
        peer_widget.setVisible(False)
        form_layout.addWidget(peer_widget)

        def _on_peer_selected():
            pid = peer_combo.currentData()
            if pid:
                try:
                    counts = self.data.get_peer_contact_count(pid)
                    peer_count_lbl.setText(
                        f"{counts.get('total',0):,} contacts  |  "
                        f"{counts.get('pending',0):,} pending")
                except Exception:
                    peer_count_lbl.setText("")
            else:
                peer_count_lbl.setText("")

        peer_combo.currentIndexChanged.connect(_on_peer_selected)

        def _toggle_targets(use_peer: bool):
            use_peer_btn.setChecked(use_peer)
            use_custom_btn.setChecked(not use_peer)
            peer_widget.setVisible(use_peer)
            custom_widget.setVisible(not use_peer)

        use_peer_btn.clicked.connect(lambda: _toggle_targets(True))
        use_custom_btn.clicked.connect(lambda: _toggle_targets(False))

        # ── Message / Template ────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Message (or use template below)"))
        message_input = QTextEdit()
        message_input.setMaximumHeight(80)
        form_layout.addWidget(message_input)

        form_layout.addWidget(QLabel("Template (optional)"))
        template_combo = QComboBox()
        template_combo.addItem("None", None)
        try:
            for t in self.data.get_templates():
                template_combo.addItem(t.get('name'), t.get('id'))
        except Exception:
            pass
        form_layout.addWidget(template_combo)

        # ── Delay ─────────────────────────────────────────────────────────────
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay Min (s):"))
        delay_min = QSpinBox()
        delay_min.setRange(1, 3600)
        delay_min.setValue(30)
        delay_layout.addWidget(delay_min)
        delay_layout.addWidget(QLabel("Delay Max (s):"))
        delay_max = QSpinBox()
        delay_max.setRange(1, 3600)
        delay_max.setValue(60)
        delay_layout.addWidget(delay_max)
        delay_layout.addStretch()
        form_layout.addLayout(delay_layout)

        rotate_accounts = QCheckBox("Rotate Accounts")
        rotate_accounts.setChecked(True)
        form_layout.addWidget(rotate_accounts)
        auto_retry = QCheckBox("Auto Retry Failed")
        form_layout.addWidget(auto_retry)

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Create Campaign")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['gradient_green']};
                border: none; border-radius: 8px;
                color: white; font-weight: 600; padding: 10px 24px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_green_dark']}; }}
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        def save():
            if not name_input.text().strip():
                toast_warning("Enter a campaign name")
                return
            selected = accounts_list.selectedItems()
            account_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected]
            if not account_ids:
                toast_warning("Select at least one account")
                return

            # Resolve targets — peer or custom
            if use_peer_btn.isChecked():
                peer_id = peer_combo.currentData()
                if not peer_id:
                    toast_warning("Select a peer")
                    return
                try:
                    targets = self.data.get_peer_targets(peer_id)
                    if not targets:
                        toast_warning("Selected peer has no contacts")
                        return
                    toast_info(f"Using peer: {len(targets):,} contacts")
                except Exception as e:
                    toast_error(f"Could not load peer: {e}")
                    return
            else:
                targets = [t.strip() for t in targets_input.toPlainText().strip().split('\n')
                           if t.strip()]
                if not targets:
                    toast_warning("Enter at least one target")
                    return

            if not message_input.toPlainText().strip() and not template_combo.currentData():
                toast_warning("Enter a message or select a template")
                return

            data = {
                "name":            name_input.text().strip(),
                "account_ids":     account_ids,
                "targets":         targets,
                "message_text":    message_input.toPlainText(),
                "template_id":     template_combo.currentData(),
                "delay_min":       delay_min.value(),
                "delay_max":       delay_max.value(),
                "rotate_accounts": rotate_accounts.isChecked(),
                "auto_retry":      auto_retry.isChecked(),
            }
            try:
                self.data.create_campaign(data)
                toast_success(f"Campaign created — {len(targets):,} targets")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to create: {e}")

        save_btn.clicked.connect(save)
        dialog.exec()

    def run_campaign(self, campaign: Campaign):
        try:
            result = self.data.run_campaign(campaign.id)
            job_id = result.get("job_id", "")
            toast_success(f"Campaign '{campaign.name}' started")
            self.fetch_data()
            # Show live dashboard if we have a job_id
            if job_id:
                from campaign_dialog import CampaignLiveDialog
                dialog = CampaignLiveDialog(self, job_id=job_id, api_client=self.data)
                dialog.campaign_completed.connect(self.fetch_data)
                dialog.show()
        except Exception as e:
            toast_error(f"Failed to run: {e}")

    def edit_campaign(self, campaign: Campaign):
        """Edit campaign — full form with peer selector, template, accounts."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit — {campaign.name}")
        dialog.setMinimumSize(560, 680)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {COLORS['bg_secondary']}; }}
            QLabel {{ color: {COLORS['text_primary']}; font-size: 13px; }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px;
                color: {COLORS['text_primary']};
            }}
            QListWidget {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QCheckBox {{ color: {COLORS['text_primary']}; spacing: 8px; }}
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 16px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(scroll_widget)
        form_layout.setSpacing(10)

        # ── Name ──────────────────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Campaign Name *"))
        name_input = QLineEdit(campaign.name)
        form_layout.addWidget(name_input)

        # ── Accounts ──────────────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Select Accounts (Ctrl+Click for multiple)"))
        accounts_list = QListWidget()
        accounts_list.setMaximumHeight(100)
        accounts_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        try:
            all_accs = self.data.get_accounts()
            for acc in all_accs:
                item = QListWidgetItem(
                    f"{acc.get('name') or acc.get('phone')} ({acc.get('status')})")
                item.setData(Qt.ItemDataRole.UserRole, acc.get('id'))
                accounts_list.addItem(item)
                if acc.get('id') in campaign.account_ids:
                    item.setSelected(True)
        except Exception:
            pass
        form_layout.addWidget(accounts_list)

        # ── Targets — Peer OR Custom ──────────────────────────────────────────
        tgt_header = QHBoxLayout()
        tgt_header.addWidget(QLabel("Targets"))
        use_peer_btn   = QPushButton("👥 Use Peer")
        use_custom_btn = QPushButton("✏ Custom")
        use_peer_btn.setCheckable(True)
        use_custom_btn.setCheckable(True)
        _tgl_style = f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 5px; padding: 0 10px;
                color: {COLORS['text_secondary']}; font-size: 12px;
                min-height: 26px;
            }}
            QPushButton:checked {{
                background: {COLORS['accent_blue_dark']};
                border-color: {COLORS['accent_blue']};
                color: white; font-weight: 600;
            }}
            QPushButton:hover:!checked {{ background: {COLORS['bg_hover']}; }}
        """
        use_peer_btn.setStyleSheet(_tgl_style)
        use_custom_btn.setStyleSheet(_tgl_style)
        tgt_header.addWidget(use_custom_btn)
        tgt_header.addWidget(use_peer_btn)
        tgt_header.addStretch()
        form_layout.addLayout(tgt_header)

        # Decide initial mode from existing campaign data
        existing_peer_ids = getattr(campaign, 'peer_ids', [])
        if not isinstance(existing_peer_ids, list):
            existing_peer_ids = []
        _init_peer_mode = bool(existing_peer_ids)
        use_peer_btn.setChecked(_init_peer_mode)
        use_custom_btn.setChecked(not _init_peer_mode)

        # Custom widget
        custom_widget = QWidget()
        custom_widget.setStyleSheet("background: transparent;")
        cwl = QVBoxLayout(custom_widget)
        cwl.setContentsMargins(0, 0, 0, 0)
        targets_input = QTextEdit()
        targets_input.setMaximumHeight(90)
        targets_input.setPlaceholderText("+923001234567\n@username")
        targets_input.setPlainText("\n".join(campaign.targets))
        cwl.addWidget(targets_input)
        custom_widget.setVisible(not _init_peer_mode)
        form_layout.addWidget(custom_widget)

        # Peer widget
        peer_widget = QWidget()
        peer_widget.setStyleSheet("background: transparent;")
        pwl = QVBoxLayout(peer_widget)
        pwl.setContentsMargins(0, 0, 0, 0)
        peer_combo = QComboBox()
        peer_combo.addItem("— Select a peer —", None)
        peer_count_lbl = QLabel("")
        peer_count_lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;")
        try:
            for p in self.data.get_peers():
                peer_combo.addItem(
                    f"● {p['title']}  ({p.get('contact_count', 0):,} contacts)",
                    p["id"])
                if p["id"] in existing_peer_ids:
                    peer_combo.setCurrentIndex(peer_combo.count() - 1)
        except Exception:
            pass
        pwl.addWidget(peer_combo)
        pwl.addWidget(peer_count_lbl)
        peer_widget.setVisible(_init_peer_mode)
        form_layout.addWidget(peer_widget)

        def _on_peer_sel():
            pid = peer_combo.currentData()
            if pid:
                try:
                    c2 = self.data.get_peer_contact_count(pid)
                    peer_count_lbl.setText(
                        f"{c2.get('total',0):,} contacts  |  "
                        f"{c2.get('pending',0):,} pending")
                except Exception:
                    peer_count_lbl.setText("")
        peer_combo.currentIndexChanged.connect(_on_peer_sel)
        _on_peer_sel()

        def _toggle(use_peer):
            use_peer_btn.setChecked(use_peer)
            use_custom_btn.setChecked(not use_peer)
            peer_widget.setVisible(use_peer)
            custom_widget.setVisible(not use_peer)
        use_peer_btn.clicked.connect(lambda: _toggle(True))
        use_custom_btn.clicked.connect(lambda: _toggle(False))

        # ── Template ──────────────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Template (optional)"))
        template_combo = QComboBox()
        template_combo.addItem("None — use custom message", None)
        try:
            for t in self.data.get_templates():
                template_combo.addItem(t.get('name'), t.get('id'))
                if t.get('id') == campaign.template_id:
                    template_combo.setCurrentIndex(template_combo.count() - 1)
        except Exception:
            pass
        form_layout.addWidget(template_combo)

        # ── Message ───────────────────────────────────────────────────────────
        form_layout.addWidget(QLabel("Custom Message (ignored if template selected)"))
        message_input = QTextEdit()
        message_input.setMaximumHeight(80)
        message_input.setPlainText(campaign.message_text)
        form_layout.addWidget(message_input)

        # ── Delay ─────────────────────────────────────────────────────────────
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay Min (s):"))
        delay_min = QSpinBox()
        delay_min.setRange(1, 3600)
        delay_min.setValue(campaign.delay_min)
        delay_layout.addWidget(delay_min)
        delay_layout.addWidget(QLabel("Delay Max (s):"))
        delay_max = QSpinBox()
        delay_max.setRange(1, 3600)
        delay_max.setValue(campaign.delay_max)
        delay_layout.addWidget(delay_max)
        delay_layout.addWidget(QLabel("Max/account:"))
        max_per = QSpinBox()
        max_per.setRange(0, 9999)
        max_per.setSpecialValueText("Unlimited")
        max_per.setValue(campaign.max_per_account or 0)
        delay_layout.addWidget(max_per)
        delay_layout.addStretch()
        form_layout.addLayout(delay_layout)

        options_row = QHBoxLayout()
        rotate_cb = QCheckBox("Rotate Accounts")
        rotate_cb.setChecked(bool(getattr(campaign, 'rotate_accounts', True)))
        retry_cb  = QCheckBox("Auto Retry Failed")
        retry_cb.setChecked(bool(campaign.auto_retry))
        options_row.addWidget(rotate_cb)
        options_row.addWidget(retry_cb)
        options_row.addStretch()
        form_layout.addLayout(options_row)

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['gradient_blue']};
                border: none; border-radius: 8px;
                color: white; font-weight: 600; padding: 10px 24px;
            }}
            QPushButton:hover {{ background: {COLORS['accent_blue_dark']}; }}
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        def save():
            if not name_input.text().strip():
                toast_warning("Enter a campaign name")
                return
            selected_accs = accounts_list.selectedItems()
            account_ids = [i.data(Qt.ItemDataRole.UserRole) for i in selected_accs]

            # Targets
            if use_peer_btn.isChecked():
                pid = peer_combo.currentData()
                if not pid:
                    toast_warning("Select a peer")
                    return
                try:
                    targets = self.data.get_peer_targets(pid)
                    peer_ids_save = [pid]
                except Exception as e:
                    toast_error(f"Could not load peer: {e}")
                    return
            else:
                targets = [t.strip() for t in
                           targets_input.toPlainText().split("\n") if t.strip()]
                peer_ids_save = []

            tid = template_combo.currentData()
            msg = message_input.toPlainText().strip()
            if not tid and not msg:
                toast_warning("Enter a message or select a template")
                return

            try:
                self.data.update_campaign(campaign.id, {
                    "name":            name_input.text().strip(),
                    "account_ids":     account_ids,
                    "targets":         targets,
                    "peer_ids":        peer_ids_save,
                    "template_id":     tid,
                    "message_text":    msg,
                    "delay_min":       delay_min.value(),
                    "delay_max":       delay_max.value(),
                    "max_per_account": max_per.value(),
                    "rotate_accounts": rotate_cb.isChecked(),
                    "auto_retry":      retry_cb.isChecked(),
                })
                toast_success("Campaign updated!")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed: {e}")

        save_btn.clicked.connect(save)
        dialog.exec()

    def pause_campaign(self, campaign: Campaign):
        try:
            self.data.update_campaign(campaign.id, {"status": "paused"})
            toast_info(f"Campaign '{campaign.name}' paused")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Failed to pause: {e}")

    def schedule_campaign(self, campaign: Campaign):
        try:
            self.data.update_campaign(campaign.id, {"status": "scheduled"})
            toast_success(f"Campaign '{campaign.name}' scheduled")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Failed to schedule: {e}")

    def rerun_campaign(self, campaign: Campaign):
        reply = QMessageBox.question(self, "Re-run Campaign",
            f'Re-run campaign "{campaign.name}"?\n\nThis will send messages to all targets again.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset to draft first so run_campaign can transition to running
                self.data.update_campaign(campaign.id, {"status": "draft"})
                result = self.data.run_campaign(campaign.id)
                job_id = result.get("job_id", "")
                toast_success(f"Campaign '{campaign.name}' re-started")
                self.fetch_data()
                if job_id:
                    from campaign_dialog import CampaignLiveDialog
                    dlg = CampaignLiveDialog(self, job_id=job_id, api_client=self.data)
                    dlg.campaign_completed.connect(self.fetch_data)
                    dlg.show()
            except Exception as e:
                toast_error(f"Failed to re-run: {e}")

    def delete_campaign(self, campaign: Campaign):
        reply = QMessageBox.question(self, "Delete Campaign", f"Delete '{campaign.name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_campaign(campaign.id)
                toast_success("Campaign deleted")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to delete: {e}")


class ScraperPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.accounts = []
        self.scraped_members = []
        self.init_ui()
        self.fetch_accounts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        title_icon = QLabel("🔍")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        title = QLabel("Scraper")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addWidget(title_container)

        tabs = QTabWidget()
        scrape_widget = QWidget()
        scrape_layout = QVBoxLayout(scrape_widget)
        scrape_layout.addWidget(QLabel("Select Account:"))
        self.scrape_account_combo = QComboBox()
        scrape_layout.addWidget(self.scrape_account_combo)
        scrape_layout.addWidget(QLabel("Group (username or invite link):"))
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("@groupname or https://t.me/+xxxxx")
        scrape_layout.addWidget(self.group_input)
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Limit:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 10000)
        self.limit_spin.setValue(0)
        self.limit_spin.setSpecialValueText("No limit")
        settings_layout.addWidget(self.limit_spin)
        settings_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["all", "active", "recent"])
        settings_layout.addWidget(self.filter_combo)
        settings_layout.addStretch()
        scrape_layout.addLayout(settings_layout)
        self.start_scrape_btn = QPushButton("Start Scraping")
        self.start_scrape_btn.setProperty("primary", True)
        self.start_scrape_btn.clicked.connect(self.start_scrape)
        scrape_layout.addWidget(self.start_scrape_btn)
        self.scrape_status = QLabel("")
        scrape_layout.addWidget(self.scrape_status)
        scrape_layout.addWidget(QLabel("Results:"))
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "First Name", "Last Name", "Username", "Phone"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(0, 100)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                gridline-color: {COLORS['border_light']};
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31,111,235,0.2);
                color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                padding: 12px;
                border: none;
                font-weight: 600;
                color: {COLORS['text_secondary']};
            }}
        """)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        scrape_layout.addWidget(self.results_table)
        export_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(self.export_csv_btn)
        self.copy_usernames_btn = QPushButton("Copy Usernames")
        self.copy_usernames_btn.clicked.connect(self.copy_usernames)
        export_layout.addWidget(self.copy_usernames_btn)
        export_layout.addStretch()
        scrape_layout.addLayout(export_layout)
        tabs.addTab(scrape_widget, "Scrape Members")

        join_widget = QWidget()
        join_layout = QVBoxLayout(join_widget)
        join_layout.addWidget(QLabel("Select Accounts:"))
        self.join_accounts_list = QListWidget()
        self.join_accounts_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        join_layout.addWidget(self.join_accounts_list)
        join_layout.addWidget(QLabel("Groups (one per line):"))
        self.join_groups_input = QTextEdit()
        self.join_groups_input.setMaximumHeight(150)
        join_layout.addWidget(self.join_groups_input)
        join_delay_layout = QHBoxLayout()
        join_delay_layout.addWidget(QLabel("Delay Min (s):"))
        self.join_delay_min = QSpinBox()
        self.join_delay_min.setValue(10)
        join_delay_layout.addWidget(self.join_delay_min)
        join_delay_layout.addWidget(QLabel("Delay Max (s):"))
        self.join_delay_max = QSpinBox()
        self.join_delay_max.setValue(30)
        join_delay_layout.addWidget(self.join_delay_max)
        join_delay_layout.addStretch()
        join_layout.addLayout(join_delay_layout)
        self.start_join_btn = QPushButton("Start Joining")
        self.start_join_btn.setProperty("success", True)
        self.start_join_btn.clicked.connect(self.start_join)
        join_layout.addWidget(self.start_join_btn)
        self.join_status = QLabel("")
        join_layout.addWidget(self.join_status)
        join_layout.addStretch()
        tabs.addTab(join_widget, "Join Groups")
        layout.addWidget(tabs)

    def fetch_accounts(self):
        try:
            data = self.data.get_accounts()
            self.accounts = [Account.from_dict(a) for a in data]
            self.scrape_account_combo.clear()
            for account in self.accounts:
                self.scrape_account_combo.addItem(f"{account.name or account.phone} ({account.status})", account.id)
            self.join_accounts_list.clear()
            for account in self.accounts:
                item = QListWidgetItem(f"{account.name or account.phone}")
                item.setData(Qt.ItemDataRole.UserRole, account.id)
                self.join_accounts_list.addItem(item)
        except Exception as e:
            toast_error(f"Failed to fetch accounts: {e}")

    def start_scrape(self):
        account_id = self.scrape_account_combo.currentData()
        if not account_id:
            toast_warning("Please select an account")
            return
        group = self.group_input.text().strip()
        if not group:
            toast_warning("Please enter a group")
            return
        try:
            limit = self.limit_spin.value()
            filter_type = self.filter_combo.currentText()
            job_id = self.data.scrape_members(account_id, group, limit, filter_type)
            self.scrape_status.setText("Scraping…")
            self.start_scrape_btn.setEnabled(False)
            self._poll_scrape(job_id)
        except Exception as e:
            toast_error(f"Failed to start scrape: {e}")

    def _poll_scrape(self, job_id: str):
        try:
            status = self.data.get_job_status(job_id)
            if status is None:
                return
            job_status = status.get("status", "unknown")
            self.scrape_status.setText(f"Status: {job_status}")
            if job_status == "completed":
                self.start_scrape_btn.setEnabled(True)
                self.scraped_members = [ScrapedMember.from_dict(m) for m in status.get("members", [])]
                self.update_results_table()
                toast_success(f"Scraped {len(self.scraped_members)} members")
            elif job_status == "failed":
                self.start_scrape_btn.setEnabled(True)
                toast_error(f"Scraping failed: {status.get('message', '')}")
            else:
                QTimer.singleShot(1500, lambda: self._poll_scrape(job_id))
        except Exception as e:
            self.start_scrape_btn.setEnabled(True)
            toast_error(f"Status check failed: {e}")

    def update_results_table(self):
        self.results_table.setRowCount(len(self.scraped_members))
        for row, member in enumerate(self.scraped_members):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(member.user_id)))
            self.results_table.setItem(row, 1, QTableWidgetItem(member.first_name))
            self.results_table.setItem(row, 2, QTableWidgetItem(member.last_name))
            self.results_table.setItem(row, 3, QTableWidgetItem(member.username))
            self.results_table.setItem(row, 4, QTableWidgetItem(member.phone))

    def export_csv(self):
        if not self.scraped_members:
            toast_warning("No members to export")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "members.csv", "CSV Files (*.csv)")
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("user_id,first_name,last_name,username,phone,status\n")
                for member in self.scraped_members:
                    f.write(member.to_csv_row() + "\n")
            toast_success(f"Exported to {file_path}")
        except Exception as e:
            toast_error(f"Export failed: {e}")

    def copy_usernames(self):
        usernames = [f"@{m.username}" for m in self.scraped_members if m.username]
        if not usernames:
            toast_warning("No usernames to copy")
            return
        QApplication.clipboard().setText('\n'.join(usernames))
        toast_success(f"Copied {len(usernames)} usernames to clipboard")

    def start_join(self):
        selected = self.join_accounts_list.selectedItems()
        if not selected:
            toast_warning("Please select at least one account")
            return
        groups_text = self.join_groups_input.toPlainText().strip()
        if not groups_text:
            toast_warning("Please enter at least one group")
            return
        account_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected]
        groups = [g.strip() for g in groups_text.split("\n") if g.strip()]
        try:
            job_id = self.data.join_groups(
                account_ids, groups,
                self.join_delay_min.value(), self.join_delay_max.value())
            self.join_status.setText("Joining…")
            self.start_join_btn.setEnabled(False)
            self._poll_join(job_id)
        except Exception as e:
            toast_error(f"Failed to start join: {e}")

    def _poll_join(self, job_id: str):
        try:
            status = self.data.get_job_status(job_id)
            if status is None:
                return
            job_status = status.get("status", "unknown")
            joined  = status.get("sent", 0)
            failed  = status.get("failed", 0)
            total   = status.get("total", 0)
            self.join_status.setText(f"Joined {joined}/{total}, failed {failed}")
            if job_status in ("completed", "failed", "cancelled"):
                self.start_join_btn.setEnabled(True)
                if job_status == "completed":
                    toast_success(f"Done: joined {joined}, failed {failed}")
                else:
                    toast_error(f"Join {job_status}: {status.get('message','')}")
            else:
                QTimer.singleShot(2000, lambda: self._poll_join(job_id))
        except Exception as e:
            self.start_join_btn.setEnabled(True)
            toast_error(f"Join status check failed: {e}")


class ProxiesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.proxies = []
        self.init_ui()
        self.fetch_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        header = QHBoxLayout()
        title_icon = QLabel("🌐")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        title = QLabel("Proxies")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        header.addWidget(title)
        header.addStretch()
        self.bulk_btn = QPushButton("Bulk Import")
        self.bulk_btn.clicked.connect(self.bulk_import)
        header.addWidget(self.bulk_btn)
        self.add_btn = QPushButton("+ Add Proxy")
        self.add_btn.setProperty("primary", True)
        self.add_btn.clicked.connect(self.add_proxy)
        header.addWidget(self.add_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Type", "Host", "Port", "Username", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 60)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 150)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                gridline-color: {COLORS['border_light']};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31,111,235,0.2);
                color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                padding: 12px;
                border: none;
                font-weight: 600;
                color: {COLORS['text_secondary']};
            }}
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def fetch_data(self):
        try:
            self.proxies = [Proxy.from_dict(p) for p in self.data.get_proxies()]
            self.update_table()
        except Exception as e:
            toast_error(f"Failed to fetch proxies: {e}")

    def update_table(self):
        self.table.setRowCount(len(self.proxies))
        for row, proxy in enumerate(self.proxies):
            self.table.setItem(row, 0, QTableWidgetItem(proxy.scheme))
            self.table.setItem(row, 1, QTableWidgetItem(proxy.host))
            self.table.setItem(row, 2, QTableWidgetItem(str(proxy.port)))
            self.table.setItem(row, 3, QTableWidgetItem(proxy.username or "None"))
            status_item = QTableWidgetItem("Active" if proxy.is_active else "Inactive")
            status_item.setForeground(QColor(COLORS['accent_green'] if proxy.is_active else COLORS['accent_red']))
            self.table.setItem(row, 4, status_item)

            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            al = QHBoxLayout(actions_widget)
            al.setContentsMargins(6, 4, 6, 4)
            al.setSpacing(5)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)

            test_btn = QPushButton("⚡ Test")
            test_btn.setFixedHeight(30)
            test_btn.setMinimumWidth(68)
            test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            test_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #58A6FF,stop:1 #1F6FEB);
                    border: none; border-radius: 6px;
                    color: white; font-weight: 600; font-size: 11px; padding: 0px 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD);
                }
            """)
            test_btn.clicked.connect(lambda _, p=proxy: self.test_proxy(p))
            al.addWidget(test_btn)

            del_proxy_btn = QPushButton("✕ Del")
            del_proxy_btn.setFixedHeight(30)
            del_proxy_btn.setMinimumWidth(56)
            del_proxy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_proxy_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F85149,stop:1 #DA3633);
                    border: none; border-radius: 6px;
                    color: white; font-weight: 600; font-size: 11px; padding: 0px 8px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149);
                }
            """)
            del_proxy_btn.clicked.connect(lambda _, p=proxy: self.delete_proxy(p))
            al.addWidget(del_proxy_btn)

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 44)

    def add_proxy(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Proxy")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Type:"))
        scheme_combo = QComboBox()
        scheme_combo.addItems(["socks5", "socks4", "http"])
        layout.addWidget(scheme_combo)
        layout.addWidget(QLabel("Host:"))
        host_input = QLineEdit()
        host_input.setPlaceholderText("127.0.0.1")
        layout.addWidget(host_input)
        layout.addWidget(QLabel("Port:"))
        port_input = QSpinBox()
        port_input.setRange(1, 65535)
        port_input.setValue(1080)
        layout.addWidget(port_input)
        layout.addWidget(QLabel("Username (optional):"))
        username_input = QLineEdit()
        layout.addWidget(username_input)
        layout.addWidget(QLabel("Password (optional):"))
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)
        buttons = QHBoxLayout()
        save_btn = QPushButton("Add")
        save_btn.setProperty("primary", True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        def save():
            try:
                self.data.create_proxy({
                    "scheme": scheme_combo.currentText(), "host": host_input.text(),
                    "port": port_input.value(), "username": username_input.text() or None,
                    "password": password_input.text() or None,
                })
                toast_success("Proxy added")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to add: {e}")

        save_btn.clicked.connect(save)
        dialog.exec()

    def bulk_import(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Bulk Import Proxies")
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Paste proxies (one per line):"))
        layout.addWidget(QLabel("Formats: host:port, user:pass@host:port, scheme://host:port"))
        text_input = QTextEdit()
        layout.addWidget(text_input)
        buttons = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.setProperty("primary", True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addStretch()
        buttons.addWidget(import_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        def do_import():
            raw = text_input.toPlainText().strip()
            if not raw:
                toast_warning("Please enter at least one proxy")
                return
            try:
                result = self.data.bulk_create_proxies(raw)
                toast_success(
                    f"Imported {result['imported']}, "
                    f"skipped {result['skipped']}, "
                    f"failed {result['failed']}")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Import failed: {e}")

        import_btn.clicked.connect(do_import)
        dialog.exec()

    def test_proxy(self, proxy: Proxy):
        try:
            result = self.data.test_proxy(proxy.id)
            if result.get("ok"):
                toast_success(f"Proxy OK: {result['message']}")
            else:
                toast_error(f"Proxy failed: {result['message']}")
        except Exception as e:
            toast_error(f"Proxy test error: {e}")

    def delete_proxy(self, proxy: Proxy):
        reply = QMessageBox.question(self, "Delete Proxy", f"Delete proxy {proxy.host}:{proxy.port}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_proxy(proxy.id)
                toast_success("Proxy deleted")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to delete: {e}")


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.init_ui()
        self.fetch_logs()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        header = QHBoxLayout()
        title_icon = QLabel("📋")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        title = QLabel("Logs")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        header.addWidget(title)
        header.addStretch()
        self.clear_btn = QPushButton("Clear Logs")
        self.clear_btn.setProperty("danger", True)
        self.clear_btn.clicked.connect(self.clear_logs)
        header.addWidget(self.clear_btn)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.fetch_logs)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["All", "info", "warn", "error"])
        self.level_combo.currentTextChanged.connect(lambda _: self.fetch_logs())
        filters_layout.addWidget(self.level_combo)
        filters_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "auth", "message", "campaign", "scrape", "general"])
        self.category_combo.currentTextChanged.connect(lambda _: self.fetch_logs())
        filters_layout.addWidget(self.category_combo)
        filters_layout.addStretch()
        layout.addLayout(filters_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Level", "Category", "Time", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col, w in [(0,70),(1,100),(2,140)]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def fetch_logs(self):
        category = self.category_combo.currentText()
        level    = self.level_combo.currentText()
        try:
            logs_raw = self.data.get_logs(
                category if category != "All" else None, 200)
            logs = [Log.from_dict(l) for l in logs_raw]
            # Apply level filter client-side (service returns all levels)
            if level != "All":
                logs = [l for l in logs if l.level == level]
            self.update_table(logs)
        except Exception as e:
            toast_error(f"Failed to fetch logs: {e}")

    def update_table(self, logs: list):
        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            level_item = QTableWidgetItem(log.level.upper())
            if log.level == "error":
                level_item.setForeground(QColor(COLORS['accent_red']))
            elif log.level == "warn":
                level_item.setForeground(QColor(COLORS['accent_yellow']))
            else:
                level_item.setForeground(QColor(COLORS['accent_blue']))
            self.table.setItem(row, 0, level_item)
            self.table.setItem(row, 1, QTableWidgetItem(log.category))
            time_str = log.created_at.replace('T', ' ')[:19] if log.created_at else ""
            self.table.setItem(row, 2, QTableWidgetItem(time_str))
            self.table.setItem(row, 3, QTableWidgetItem(log.message))

    def clear_logs(self):
        reply = QMessageBox.question(self, "Clear Logs", "Clear all logs?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
                result = self.data.clear_logs()
                toast_success(f"Cleared {result.get('deleted', 0)} logs")
                self.fetch_logs()


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.settings = None
        self.init_ui()
        self.fetch_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        title_icon = QLabel("⚙️")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['text_primary']}; padding-left: 12px;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addWidget(title_container)

        api_group = QGroupBox("Telegram API Credentials")
        api_layout = QGridLayout(api_group)
        api_layout.addWidget(QLabel("API ID:"), 0, 0)
        self.data_id_input = QSpinBox()
        self.data_id_input.setRange(0, 999999999)
        api_layout.addWidget(self.data_id_input, 0, 1)
        api_layout.addWidget(QLabel("API Hash:"), 1, 0)
        self.data_hash_input = QLineEdit()
        self.data_hash_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.data_hash_input.setPlaceholderText("Leave empty to keep current")
        api_layout.addWidget(self.data_hash_input, 1, 1)
        layout.addWidget(api_group)

        msg_group = QGroupBox("Messaging Defaults")
        msg_layout = QGridLayout(msg_group)
        msg_layout.addWidget(QLabel("Delay Min (sec):"), 0, 0)
        self.delay_min = QSpinBox()
        self.delay_min.setRange(1, 3600)
        msg_layout.addWidget(self.delay_min, 0, 1)
        msg_layout.addWidget(QLabel("Delay Max (sec):"), 1, 0)
        self.delay_max = QSpinBox()
        self.delay_max.setRange(1, 3600)
        msg_layout.addWidget(self.delay_max, 1, 1)
        msg_layout.addWidget(QLabel("Max Per Account:"), 2, 0)
        self.max_per_account = QSpinBox()
        self.max_per_account.setRange(0, 1000)
        msg_layout.addWidget(self.max_per_account, 2, 1)
        msg_layout.addWidget(QLabel("Flood Wait Cap:"), 3, 0)
        self.flood_wait_cap = QSpinBox()
        self.flood_wait_cap.setRange(1, 3600)
        msg_layout.addWidget(self.flood_wait_cap, 3, 1)
        layout.addWidget(msg_group)
        layout.addStretch()

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setProperty("primary", True)
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

    def fetch_settings(self):
        try:
            data = self.data.get_settings()
            self.settings = Settings.from_dict(data)
            self.data_id_input.setValue(self.settings.api_id)
            self.delay_min.setValue(self.settings.default_delay_min)
            self.delay_max.setValue(self.settings.default_delay_max)
            self.max_per_account.setValue(self.settings.max_per_account)
            self.flood_wait_cap.setValue(self.settings.flood_wait_cap)
        except Exception as e:
            toast_error(f"Failed to fetch settings: {e}")

    def save_settings(self):
        data = {
            "api_id": self.data_id_input.value(),
            "api_hash": self.data_hash_input.text() or None,
            "default_delay_min": self.delay_min.value(),
            "default_delay_max": self.delay_max.value(),
            "max_per_account": self.max_per_account.value(),
            "flood_wait_cap": self.flood_wait_cap.value(),
        }
        try:
            self.data.save_settings(data)
            toast_success("Settings saved!")
        except Exception as e:
            toast_error(f"Failed to save: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TG-PY")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)
        self.setStyleSheet(ModernStyle.get_main_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.pages = {
            "Dashboard": DashboardPage(),
            "Accounts":  AccountsPage(),
            "Messaging": MessagingPage(),
            "Campaigns": CampaignsPage(),
            "Scraper":   ScraperPage(),
            "Proxies":   ProxiesPage(),
            "Templates": TemplatesPage(),
            "Contacts":  ContactsPage(),
            "Logs":      LogsPage(),
            "Settings":  SettingsPage(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_frame, 1)

        self.sidebar = Sidebar(self.navigate)
        main_layout.insertWidget(0, self.sidebar)

        init_toast_manager(self)
        self.navigate("Dashboard")

    def navigate(self, page_name):
        if page_name in self.pages:
            self.stack.setCurrentIndex(list(self.pages.keys()).index(page_name))
            for name, btn in self.sidebar.buttons.items():
                btn.set_active(name == page_name)
            # ── Invalidate cache on every page switch ─────────────────────────
            # Ensures DB changes made externally are visible immediately
            try:
                data_service.invalidate_all()
            except Exception:
                pass
            # Call fetch_data/fetch_stats on the active page
            page = self.pages[page_name]
            if hasattr(page, 'fetch_data'):
                page.fetch_data()
            elif hasattr(page, 'fetch_stats'):
                page.fetch_stats()
            elif hasattr(page, 'load_data'):
                page.load_data()

    def check_backend(self):
        pass  # Backend is integrated; no health check needed


def main():
    """
    Full application entry point — license check + main window.
    This is the ONLY entry point. app.py is no longer needed.
    """
    import logging
    import builtins
    import base64
    from PyQt6.QtCore import QTimer

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # ── ENCRYPTED LICENSE SERVER CREDENTIALS ──────────────────────────────────
    # These are embedded in the EXE - user cannot access or modify
    # Encryption: Base64 + XOR obfuscation

    def _decrypt_config(encrypted: str) -> str:
        """Simple XOR decryption for config values."""
        key = 0x5A
        decoded = base64.b64decode(encrypted).decode('utf-8')
        return ''.join(chr(ord(c) ^ key) for c in decoded)

    # Encrypted Supabase credentials (XOR + Base64) - GENERATED BY generate_encrypted.py
    _ENCRYPTED_DB_HOST = "Oy0pd2t3Oyp3NDUoLjI/Oykud2t0KjU1Nj8odCkvKjs4Oyk/dDk1Nw=="
    _ENCRYPTED_DB_USER = "KjUpLj0oPyl0PC4pNDk2Nz0zKz03NDAsNS8sMz0="
    _ENCRYPTED_DB_PASS = "Dig7Pj82Myw/Ymxoa21taA=="

    # Set environment variables BEFORE license.db imports
    os.environ['TGPY_DB_HOST'] = _decrypt_config(_ENCRYPTED_DB_HOST)
    os.environ['TGPY_DB_USER'] = _decrypt_config(_ENCRYPTED_DB_USER)
    os.environ['TGPY_DB_PASS'] = _decrypt_config(_ENCRYPTED_DB_PASS)
    os.environ['TGPY_DB_PORT'] = "5432"
    os.environ['TGPY_DB_NAME'] = "postgres"

    logger.info("License server config loaded (encrypted)")

    app = QApplication(sys.argv)
    app.setApplicationName("TG-PY")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ── License check ─────────────────────────────────────────────────────────
    from license.hardware import get_hardware_id
    from license.checker import periodic_check
    from license.activation_ui import ActivationDialog, LicenseExpiredDialog

    hardware_id = get_hardware_id()
    logger.info("Hardware ID: %s...", hardware_id[:8])

    dlg = ActivationDialog()
    if dlg.exec() != 1:
        sys.exit(0)

    result = dlg.license_result
    if not result or not result.ok:
        sys.exit(0)

    builtins.TGPY_LICENSE = result
    logger.info("License OK: %s / %s / %s days",
                result.username, result.plan, result.days_remaining)

    # ── Background periodic license check every 6 hours ──────────────────────
    def _bg_license_check():
        try:
            r = periodic_check(result.username, hardware_id)
            if not r.ok:
                exp = LicenseExpiredDialog(r.message)
                exp.exec()
        except Exception as e:
            logger.error("BG license check error: %s", e)

    _lic_timer = QTimer()
    _lic_timer.timeout.connect(_bg_license_check)
    _lic_timer.start(6 * 3600 * 1000)  # 6 hours
    builtins.TGPY_LICENSE_TIMER = _lic_timer

    # ── Start data service ────────────────────────────────────────────────────
    from data_service import get_data_service
    data_service_inst = get_data_service()
    data_service_inst.connect()

    # ── Launch main window ────────────────────────────────────────────────────
    window = MainWindow()
    window.show()
    logger.info("TG-PY started")

    try:
        exit_code = app.exec()
    finally:
        data_service_inst.disconnect()
        try:
            from license.db import close as _lic_close
            _lic_close()
        except Exception:
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
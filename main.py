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

# Get data service (replaces API client)
data_service = get_data_service()
MEDIA_BASE_URL = ""  # No longer needed with direct file access

# Enhanced Color Palette with Gradients
COLORS = {
    # Base colors
    'bg_primary': '#0D1117',      # Darker background
    'bg_secondary': '#161B22',    # Card background
    'bg_tertiary': '#21262D',     # Elevated elements
    'bg_hover': '#30363D',        # Hover state
    'bg_selected': '#1F6FEB',   # GitHub blue accent
    
    # Text colors
    'text_primary': '#F0F6FC',   # Primary text
    'text_secondary': '#8B949E',  # Secondary text
    'text_muted': '#6E7681',      # Muted text
    'text_inverse': '#0D1117',   # Text on bright backgrounds
    
    # Border
    'border': '#30363D',          # Border color
    'border_light': '#21262D',    # Lighter border
    
    # Accents with gradients
    'accent_blue': '#58A6FF',     # Primary accent
    'accent_blue_dark': '#1F6FEB',
    'accent_green': '#3FB950',    # Success
    'accent_green_dark': '#238636',
    'accent_red': '#F85149',      # Error
    'accent_red_dark': '#DA3633',
    'accent_yellow': '#D29922',     # Warning
    'accent_yellow_dark': '#9E6A03',
    'accent_purple': '#A371F7',   # Purple accent
    'accent_pink': '#F778BA',     # Pink accent
    'accent_cyan': '#39CFCF',     # Cyan accent
    
    # Gradients (for use in stylesheets)
    'gradient_blue': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #58A6FF, stop:1 #1F6FEB)',
    'gradient_green': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3FB950, stop:1 #238636)',
    'gradient_red': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F85149, stop:1 #DA3633)',
    'gradient_purple': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #A371F7, stop:1 #8957E5)',
    'gradient_card': 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #21262D, stop:1 #161B22)',
    
    # Sidebar
    'sidebar_bg': '#0D1117',
}


class ModernStyle:
    """Modern dark theme stylesheet with enhanced visuals"""

    @staticmethod
    def get_main_stylesheet():
        return f"""
            QMainWindow {{
                background-color: {COLORS['bg_primary']};
            }}
            QWidget {{
                background-color: transparent;
                color: {COLORS['text_primary']};
                font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                padding: 2px;
            }}
            QLabel[secondary="true"] {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}
            
            /* Enhanced Buttons */
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 10px 18px;
                color: {COLORS['text_primary']};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_blue']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['bg_selected']};
            }}
            
            /* Primary Button with Gradient */
            QPushButton[primary="true"] {{
                background: {COLORS['gradient_blue']};
                border: none;
                color: white;
                font-weight: 600;
            }}
            QPushButton[primary="true"]:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD);
            }}
            
            /* Success Button */
            QPushButton[success="true"] {{
                background: {COLORS['gradient_green']};
                border: none;
                color: white;
                font-weight: 600;
            }}
            QPushButton[success="true"]:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #56D364, stop:1 #2EA043);
            }}
            
            /* Danger Button */
            QPushButton[danger="true"] {{
                background: {COLORS['gradient_red']};
                border: none;
                color: white;
                font-weight: 600;
            }}
            QPushButton[danger="true"]:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7B72, stop:1 #F85149);
            }}
            
            /* Sidebar Frame */
            QFrame[sidebar="true"] {{
                background-color: {COLORS['sidebar_bg']};
                border-right: 1px solid {COLORS['border']};
            }}
            
            /* Enhanced Card with Glow Effect */
            QFrame[card="true"] {{
                background: {COLORS['gradient_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 20px;
            }}
            QFrame[card="true"]:hover {{
                border-color: {COLORS['accent_blue_dark']};
            }}
            
            /* Input Fields */
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{
                background-color: {COLORS['bg_primary']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 10px 14px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {COLORS['accent_blue']};
                background-color: {COLORS['bg_secondary']};
            }}
            QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover {{
                border-color: {COLORS['bg_hover']};
            }}
            
            /* Table Styling */
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['bg_selected']};
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31, 111, 235, 0.3);
                color: {COLORS['text_primary']};
            }}
            QTableWidget::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                padding: 12px;
                border: none;
                font-weight: 600;
                color: {COLORS['text_secondary']};
            }}
            
            /* Tab Widget */
            QTabWidget::pane {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                padding: 12px 24px;
                margin-right: 6px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                color: {COLORS['text_secondary']};
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_secondary']};
                border-bottom-color: {COLORS['bg_secondary']};
                color: {COLORS['accent_blue']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
            }}
            
            /* List Widget */
            QListWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 8px;
                margin: 2px 0;
            }}
            QListWidget::item:selected {{
                background-color: rgba(31, 111, 235, 0.2);
                border: 1px solid {COLORS['accent_blue_dark']};
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            
            /* Group Box */
            QGroupBox {{
                color: {COLORS['text_secondary']};
                font-weight: 600;
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                margin-top: 12px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: {COLORS['accent_blue']};
            }}
            
            /* Scroll Bar */
            QScrollBar:vertical {{
                background-color: {COLORS['bg_primary']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['bg_hover']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['text_muted']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            /* Progress Bar */
            QProgressBar {{
                background-color: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 8px;
                text-align: center;
                font-weight: 500;
            }}
            QProgressBar::chunk {{
                background: {COLORS['gradient_green']};
                border-radius: 8px;
            }}
            
            /* Combo Box Dropdown */
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLORS['text_secondary']};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                selection-background-color: {COLORS['bg_selected']};
            }}
            
            /* Check Box */
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_primary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent_green']};
                border-color: {COLORS['accent_green']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['accent_blue']};
            }}
            
            /* Dialog */
            QDialog {{
                background-color: {COLORS['bg_primary']};
            }}
            
            /* Menu */
            QMenu {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['bg_hover']};
            }}
        """


class SidebarButton(QPushButton):
    """Enhanced sidebar navigation button with icon and animations"""

    def __init__(self, icon_text, label, parent=None):
        super().__init__(parent)
        self.icon_text = icon_text
        self.label_text = label
        self.setText(f"{icon_text}  {label}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 12px;
                padding: 12px 18px;
                color: {COLORS['text_secondary']};
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(31, 111, 235, 0.15), stop:1 rgba(31, 111, 235, 0.05));
                border-left: 3px solid {COLORS['accent_blue']};
                color: {COLORS['accent_blue']};
                font-weight: 600;
            }}
        """)

    def set_active(self, active: bool):
        self.setChecked(active)


class Sidebar(QFrame):
    """Enhanced sidebar navigation with icons"""

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

        # Enhanced Logo with gradient text effect
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_icon = QLabel("📱")
        logo_icon.setStyleSheet("font-size: 28px;")
        logo_layout.addWidget(logo_icon)
        
        logo_text = QLabel("TG-PY")
        logo_text.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['accent_blue']};
            padding-left: 8px;
        """)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        
        layout.addWidget(logo_container)

        # Separator with gradient
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 transparent, 
                stop:0.5 {COLORS['border']}, 
                stop:1 transparent);
            max-height: 1px;
        """)
        layout.addWidget(separator)
        layout.addSpacing(20)

        # Navigation items with emoji icons
        nav_items = [
            ("📊", "Dashboard", "Dashboard"),
            ("👤", "Accounts", "Accounts"),
            ("💬", "Messaging", "Messaging"),
            ("🎯", "Campaigns", "Campaigns"),
            ("🔍", "Scraper", "Scraper"),
            ("🌐", "Proxies", "Proxies"),
            ("📝", "Templates", "Templates"),
            ("📋", "Logs", "Logs"),
            ("⚙️", "Settings", "Settings"),
        ]

        for icon, label, page in nav_items:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, p=page: self.navigate_callback(p))
            self.buttons[page] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Enhanced version label
        version_container = QFrame()
        version_container.setStyleSheet(f"""
            background-color: {COLORS['bg_tertiary']};
            border-radius: 8px;
            padding: 8px;
        """)
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(12, 8, 12, 8)
        
        version_icon = QLabel("🔷")
        version_layout.addWidget(version_icon)
        
        version = QLabel("v1.0.0")
        version.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        version_layout.addWidget(version)
        version_layout.addStretch()
        
        layout.addWidget(version_container)


class StatCard(QFrame):
    """Enhanced statistics card with icon and modern styling"""

    def __init__(self, label, value, sub="", color=COLORS['text_primary'], icon="", parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        self.card_color = color
        self.icon_text = icon
        
        # Set modern card styling with subtle glow
        self.setStyleSheet(f"""
            QFrame[card="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {COLORS['bg_tertiary']}, 
                    stop:1 {COLORS['bg_secondary']});
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 4px;
            }}
            QFrame[card="true"]:hover {{
                border-color: {color};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba({self._hex_to_rgb(color)}, 0.1), 
                    stop:1 {COLORS['bg_secondary']});
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Top row with icon and label
        top_layout = QHBoxLayout()
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 24px;")
            top_layout.addWidget(icon_label)
        
        self.label = QLabel(label)
        self.label.setProperty("secondary", True)
        self.label.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']}; font-weight: 500;")
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)

        # Value with large bold font
        self.value = QLabel(str(value))
        self.value.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        layout.addWidget(self.value)

        # Subtext
        if sub:
            self.sub = QLabel(sub)
            self.sub.setProperty("secondary", True)
            self.sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']};")
            layout.addWidget(self.sub)

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to rgb string"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"

    def update_value(self, value, sub=None):
        self.value.setText(str(value))
        if sub and hasattr(self, 'sub'):
            self.sub.setText(sub)


class DashboardPage(QWidget):
    """Dashboard with statistics"""

    def __init__(self):
        super().__init__()
        self.data = data_service
        self.stats = None
        self.init_ui()

        # Poll timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.fetch_stats)
        self.poll_timer.start(10000)  # Every 10 seconds

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Enhanced Title with icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        
        title_icon = QLabel("📊")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        
        title = QLabel("Dashboard")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_container)

        # Stats grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        stats_grid.setColumnStretch(0, 1)
        stats_grid.setColumnStretch(1, 1)
        stats_grid.setColumnStretch(2, 1)
        stats_grid.setColumnStretch(3, 1)

        self.stat_cards = {
            'accounts': StatCard("Accounts", "—", "—", COLORS['accent_blue'], "👥"),
            'messages': StatCard("Messages Sent", "—", "—", COLORS['accent_green'], "✉️"),
            'success_rate': StatCard("Success Rate", "—", "", COLORS['accent_yellow'], "📈"),
            'campaigns': StatCard("Campaigns", "—", "—", COLORS['accent_purple'], "🎯"),
            'proxies': StatCard("Proxies", "—", "", COLORS['accent_cyan'], "🌐"),
            'templates': StatCard("Templates", "—", "", COLORS['accent_pink'], "📝"),
            'scrape_ops': StatCard("Scrape Ops", "—", "", COLORS['accent_yellow'], "🔍"),
            'total': StatCard("Total Messages", "—", "", COLORS['text_secondary'], "📊"),
        }

        positions = [(0, 0), (0, 1), (0, 2), (0, 3),
                     (1, 0), (1, 1), (1, 2), (1, 3)]
        for (row, col), (key, card) in zip(positions, self.stat_cards.items()):
            stats_grid.addWidget(card, row, col)

        layout.addLayout(stats_grid)

        # Bottom section - Per-account stats and Recent logs
        bottom_layout = QHBoxLayout()

        # Per-account stats
        self.accounts_group = QGroupBox("Per-Account Stats")
        self.accounts_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_secondary']};
                font-weight: 600;
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: {COLORS['accent_blue']};
            }}
        """)
        accounts_layout = QVBoxLayout(self.accounts_group)
        accounts_layout.setSpacing(8)
        accounts_layout.setContentsMargins(12, 16, 12, 12)
        self.accounts_list = QListWidget()
        self.accounts_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        accounts_layout.addWidget(self.accounts_list)
        bottom_layout.addWidget(self.accounts_group, 1)

        # Recent logs
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

        # Initial fetch
        self.fetch_stats()

    def fetch_stats(self):
        """Fetch dashboard statistics"""
        try:
            data = self.data.get_stats()
            self.stats = Stats.from_dict(data)
            self.update_display()
        except Exception as e:
            toast_error(f"Failed to fetch stats: {e}")

    def update_display(self):
        """Update UI with stats data"""
        if not self.stats:
            return

        # Update stat cards
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

        # Update per-account list
        self.accounts_list.clear()
        for acc_stat in self.stats.per_account:
            name = acc_stat.get('name') or acc_stat.get('phone', 'Unknown')
            sent = acc_stat.get('sent', 0)
            failed = acc_stat.get('failed', 0)
            total = sent + failed
            pct = (sent / total * 100) if total > 0 else 0

            item = QListWidgetItem(f"{name}: {sent} sent, {failed} failed ({pct:.0f}%)")
            self.accounts_list.addItem(item)

        if not self.stats.per_account:
            self.accounts_list.addItem("No messaging activity yet")

        # Update recent logs
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
    """Accounts management page"""

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

        # Enhanced Header with icon
        header = QHBoxLayout()
        
        title_icon = QLabel("👤")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        
        title = QLabel("Accounts")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
        header.addWidget(title)
        header.addStretch()

        # Action buttons
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

        # Status/progress area
        self.status_frame = QFrame()
        self.status_frame.setVisible(False)
        status_layout = QHBoxLayout(self.status_frame)
        self.status_label = QLabel("")
        status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        status_layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_frame)

        # Accounts table
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
        self.table.setColumnWidth(4, 80)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 80)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 130)
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
                padding: 4px 8px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31, 111, 235, 0.2);
                color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                padding: 10px 8px;
                border: none;
                font-weight: 600;
                color: {COLORS['text_secondary']};
            }}
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.table)

    def fetch_data(self):
        """Fetch accounts and proxies"""
        try:
            accounts_data = self.data.get_accounts()
            self.accounts = [Account.from_dict(a) for a in accounts_data]

            proxies_data = self.data.get_proxies()
            self.proxies = [Proxy.from_dict(p) for p in proxies_data]

            self.update_table()
        except Exception as e:
            toast_error(f"Failed to fetch data: {e}")

    def update_table(self):
        """Update accounts table"""
        self.table.setRowCount(len(self.accounts))

        for row, account in enumerate(self.accounts):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(account.id in self.selected_accounts)
            checkbox.stateChanged.connect(lambda state, aid=account.id: self.toggle_selection(aid, state))
            self.table.setCellWidget(row, 0, checkbox)

            # Phone
            self.table.setItem(row, 1, QTableWidgetItem(account.phone))

            # Name
            self.table.setItem(row, 2, QTableWidgetItem(account.name))

            # Username
            self.table.setItem(row, 3, QTableWidgetItem(account.username))

            # Status with color
            status_item = QTableWidgetItem(account.status)
            if account.status == "active":
                status_item.setForeground(QColor(COLORS['accent_green']))
            elif account.status in ("banned", "restricted"):
                status_item.setForeground(QColor(COLORS['accent_red']))
            else:
                status_item.setForeground(QColor(COLORS['accent_yellow']))
            self.table.setItem(row, 4, status_item)

            # Messages sent
            self.table.setItem(row, 5, QTableWidgetItem(str(account.messages_sent)))

            # Actions
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(3)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            check_btn = QPushButton("Check")
            check_btn.setFixedSize(58, 26)
            check_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_blue']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 2px 4px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD);
                }}
            """)
            check_btn.clicked.connect(lambda _, a=account: self.check_health(a))
            actions_layout.addWidget(check_btn)
            
            delete_btn = QPushButton("Del")
            delete_btn.setFixedSize(42, 26)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_red']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 2px 6px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7B72, stop:1 #F85149);
                }}
            """)
            delete_btn.clicked.connect(lambda _, a=account: self.delete_account(a))
            actions_layout.addWidget(delete_btn)
            
            self.table.setCellWidget(row, 6, actions_widget)
            self.table.setRowHeight(row, 36)

    def toggle_selection(self, account_id: int, state: int):
        """Toggle account selection"""
        if state == Qt.CheckState.Checked.value:
            self.selected_accounts.add(account_id)
        else:
            self.selected_accounts.discard(account_id)

    def show_add_dialog(self):
        """Show modern login dialog matching React frontend style"""
        from login_dialog import LoginDialog
        
        dialog = LoginDialog(self, proxies=self.proxies)
        dialog.account_added.connect(self.fetch_data)
        dialog.exec()

    def check_health(self, account: Account):
        """Check account health"""
        try:
            response = self.data.check_account_health(account.id)
            toast_info(f"Account {account.phone}: {response.get('status', 'unknown')}")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Health check failed: {e}")

    def check_all_health(self):
        """Check health of all accounts"""
        try:
            self.data.check_all_accounts_health()
            toast_info("Health check started for all accounts")
            QTimer.singleShot(3000, self.fetch_data)
        except Exception as e:
            toast_error(f"Failed to start health check: {e}")

    def delete_account(self, account: Account):
        """Delete single account"""
        reply = QMessageBox.question(self, "Delete Account",
                                     f"Delete account {account.phone}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_account(account.id)
                toast_success("Account deleted")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to delete: {e}")

    def delete_selected(self):
        """Delete selected accounts"""
        if not self.selected_accounts:
            toast_warning("No accounts selected")
            return

        reply = QMessageBox.question(self, "Delete Accounts",
                                     f"Delete {len(self.selected_accounts)} accounts?",
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
        """Load sessions from sessions folder"""
        try:
            job_id = self.data.load_sessions_from_folder(str(SESSIONS_DIR))

            if not job_id:
                toast_info("No sessions to load")
                return

            self.status_frame.setVisible(True)
            self.status_label.setText("Loading sessions...")
            self.progress_bar.setRange(0, 0)  # Indeterminate

            # Start polling
            self.load_polling = True
            self.poll_load_status(job_id)

        except Exception as e:
            toast_error(f"Failed to load sessions: {e}")

    def poll_load_status(self, job_id: str):
        """Poll session loading status"""
        if not self.load_polling:
            return

        try:
            status = self.data.get_job_status(job_id)

            total = status.get("total", 0)
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
        """Import accounts from tgdata folder"""
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
        """Poll tdata import status"""
        if not self.import_polling:
            return

        try:
            status = self.data.get_job_status(job_id)

            total = status.get("total", 0)
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
        self.job_poller = None
        self.selected_accounts = set()  # Track selected account IDs
        self.account_buttons = {}  # Store account toggle buttons
        self.init_ui()
        self.fetch_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Enhanced Title with icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        
        title_icon = QLabel("💬")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        
        title = QLabel("Messaging")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_container)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)
        accounts_group = QGroupBox("Select Accounts")
        accounts_layout = QVBoxLayout(accounts_group)
        
        # Account toggle buttons container
        self.accounts_container = QWidget()
        self.accounts_flow = QHBoxLayout(self.accounts_container)
        self.accounts_flow.setSpacing(8)
        self.accounts_flow.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.accounts_flow.addStretch()
        accounts_layout.addWidget(self.accounts_container)
        
        # No accounts label (shown when no accounts)
        self.no_accounts_label = QLabel("No accounts. Add one first.")
        self.no_accounts_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        self.no_accounts_label.setVisible(False)
        accounts_layout.addWidget(self.no_accounts_label)
        
        left_layout.addWidget(accounts_group)
        targets_group = QGroupBox("Targets (one per line)")
        targets_layout = QVBoxLayout(targets_group)
        self.targets_input = QTextEdit()
        self.targets_input.setPlaceholderText("@username\n+1234567890")
        self.targets_input.setMaximumHeight(150)
        targets_layout.addWidget(self.targets_input)
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

    def fetch_data(self):
        try:
            accounts_data = self.data.get_accounts()
            self.accounts = [Account.from_dict(a) for a in accounts_data]
            self.update_accounts_display()
            templates_data = self.data.get_templates()
            self.templates = [MessageTemplate.from_dict(t) for t in templates_data]
            self.template_combo.clear()
            self.template_combo.addItem("None (use custom message)", None)
            for template in self.templates:
                self.template_combo.addItem(template.name, template.id)
            self.fetch_logs()
        except Exception as e:
            toast_error(f"Failed to fetch data: {e}")
    
    def update_accounts_display(self):
        """Update account toggle buttons display"""
        # Clear existing buttons
        for btn in self.account_buttons.values():
            btn.deleteLater()
        self.account_buttons.clear()
        
        # Remove all items from layout except stretch
        while self.accounts_flow.count() > 1:
            item = self.accounts_flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.accounts:
            self.no_accounts_label.setVisible(True)
            return
        
        self.no_accounts_label.setVisible(False)
        
        # Create toggle button for each account
        for account in self.accounts:
            btn = QPushButton(f"{account.name or account.phone}")
            btn.setCheckable(True)
            btn.setChecked(account.id in self.selected_accounts)
            btn.setProperty("account_id", account.id)
            
            # Style based on selection state
            self._update_account_button_style(btn, account.id in self.selected_accounts)
            
            btn.clicked.connect(lambda checked, b=btn, aid=account.id: self.toggle_account(b, aid))
            self.account_buttons[account.id] = btn
            self.accounts_flow.insertWidget(self.accounts_flow.count() - 1, btn)
    
    def _update_account_button_style(self, btn, selected):
        """Update button style based on selection state"""
        if selected:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent_blue']};
                    border: 1px solid {COLORS['accent_blue']};
                    border-radius: 8px;
                    padding: 8px 16px;
                    color: white;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_blue_dark']};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 8px 16px;
                    color: {COLORS['text_secondary']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_hover']};
                    border-color: {COLORS['accent_blue_dark']};
                }}
            """)
    
    def toggle_account(self, btn, account_id):
        """Toggle account selection"""
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
                item = QListWidgetItem(f"[{time_str}] {log.get('message', '')}")
                self.logs_list.addItem(item)
        except:
            pass

    def send_messages(self):
        if not self.selected_accounts:
            toast_warning("Please select at least one account")
            return
        account_ids = list(self.selected_accounts)
        targets_text = self.targets_input.toPlainText().strip()
        if not targets_text:
            toast_warning("Please enter at least one target")
            return
        targets = [t.strip() for t in targets_text.split('\n') if t.strip()]
        template_id = self.template_combo.currentData()
        data = {
            "account_ids": account_ids,
            "targets": targets,
            "message": self.message_input.toPlainText(),
            "template_id": template_id,
            "delay_min": self.delay_min.value(),
            "delay_max": self.delay_max.value(),
            "mode": self.mode_combo.currentText()
        }
        try:
            response = self.data.send_messages(data)
            self.current_job = response.get("job_id")
            if self.current_job:
                toast_success("Message sending started!")
                self.start_job_polling()
            else:
                toast_error("Failed to start job")
        except Exception as e:
            toast_error(f"Failed to send: {e}")

    def start_job_polling(self):
        if self.job_poller:
            self.job_poller.stop()
        self.job_poller = JobPoller(self.current_job, f"/messaging/jobs/{self.current_job}")
        self.job_poller.status_updated.connect(self.on_job_update)
        self.job_poller.completed.connect(self.on_job_complete)
        self.job_poller.error.connect(lambda e: toast_error(f"Job poll error: {e}"))
        self.job_poller.start()

    def on_job_update(self, data: dict):
        status = data.get("status", "unknown")
        sent = data.get("sent", 0)
        failed = data.get("failed", 0)
        total = data.get("total", 0)
        self.job_status.setText(f"Status: {status} | Sent: {sent} | Failed: {failed}")
        if total > 0:
            self.job_progress.setRange(0, total)
            self.job_progress.setValue(sent + failed)

    def on_job_complete(self, data: dict):
        status = data.get("status", "unknown")
        sent = data.get("sent", 0)
        failed = data.get("failed", 0)
        if status == "completed":
            toast_success(f"Job completed! Sent: {sent}, Failed: {failed}")
        elif status == "failed":
            toast_error(f"Job failed: {data.get('message', 'Unknown error')}")
        else:
            toast_info(f"Job {status}")
        self.job_status.setText("No active job")
        self.job_progress.setValue(0)
        self.fetch_data()
        self.fetch_logs()


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
        # Enhanced Header with icon
        header = QHBoxLayout()
        
        title_icon = QLabel("🎯")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        
        title = QLabel("Campaigns")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
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
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 80)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 70)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 70)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 100)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 160)
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
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31, 111, 235, 0.2);
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
            data = self.data.get_campaigns()
            self.campaigns = [Campaign.from_dict(c) for c in data]
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
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(3)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Status-based actions
            status = campaign.status
            
            if status == 'draft':
                # Draft: Run, Schedule, Edit, Delete
                run_btn = QPushButton("Run")
                run_btn.setFixedSize(42, 26)
                run_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['gradient_green']};
                        border: none;
                        border-radius: 4px;
                        color: white;
                        font-weight: 500;
                        font-size: 10px;
                        padding: 1px 2px;
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #56D364, stop:1 #2EA043);
                    }}
                """)
                run_btn.clicked.connect(lambda _, c=campaign: self.run_campaign(c))
                actions_layout.addWidget(run_btn)
                
                if getattr(campaign, 'schedule_cron', None):
                    sched_btn = QPushButton("Sched")
                    sched_btn.setFixedSize(42, 26)
                    sched_btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {COLORS['gradient_purple']};
                            border: none;
                            border-radius: 4px;
                            color: white;
                            font-weight: 500;
                            font-size: 10px;
                            padding: 1px 2px;
                        }}
                        QPushButton:hover {{
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #A371F7, stop:1 #8957E5);
                        }}
                    """)
                    sched_btn.clicked.connect(lambda _, c=campaign: self.schedule_campaign(c))
                    actions_layout.addWidget(sched_btn)
            
            elif status in ['running', 'scheduled']:
                # Running/Scheduled: Pause
                pause_btn = QPushButton("Pause")
                pause_btn.setFixedSize(45, 26)
                pause_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['gradient_yellow']};
                        border: none;
                        border-radius: 4px;
                        color: white;
                        font-weight: 500;
                        font-size: 10px;
                        padding: 1px 2px;
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFD700, stop:1 #D29922);
                    }}
                """)
                pause_btn.clicked.connect(lambda _, c=campaign: self.pause_campaign(c))
                actions_layout.addWidget(pause_btn)
            
            elif status in ['completed', 'failed']:
                # Completed/Failed: Re-run
                rerun_btn = QPushButton("🔄")
                rerun_btn.setFixedSize(35, 26)
                rerun_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['gradient_blue']};
                        border: none;
                        border-radius: 4px;
                        color: white;
                        font-weight: 500;
                        font-size: 12px;
                        padding: 1px 2px;
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD);
                    }}
                """)
                rerun_btn.setToolTip("Re-run campaign")
                rerun_btn.clicked.connect(lambda _, c=campaign: self.rerun_campaign(c))
                actions_layout.addWidget(rerun_btn)
            
            # Always show Edit and Delete
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(42, 26)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_blue']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 1px 2px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD);
                }}
            """)
            edit_btn.clicked.connect(lambda _, c=campaign: self.edit_campaign(c))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Del")
            delete_btn.setFixedSize(40, 26)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_red']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 1px 2px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7B72, stop:1 #F85149);
                }}
            """)
            delete_btn.clicked.connect(lambda _, c=campaign: self.delete_campaign(c))
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 6, actions_widget)
            self.table.setRowHeight(row, 36)

    def create_campaign(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Campaign")
        dialog.setMinimumSize(500, 600)
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll_widget = QWidget()
        form_layout = QVBoxLayout(scroll_widget)
        form_layout.addWidget(QLabel("Campaign Name:"))
        name_input = QLineEdit()
        form_layout.addWidget(name_input)
        form_layout.addWidget(QLabel("Select Accounts:"))
        accounts_list = QListWidget()
        accounts_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        try:
            accounts_data = self.data.get_accounts()
            for acc in accounts_data:
                item = QListWidgetItem(f"{acc.get('name') or acc.get('phone')} ({acc.get('status')})")
                item.setData(Qt.ItemDataRole.UserRole, acc.get('id'))
                accounts_list.addItem(item)
        except:
            pass
        form_layout.addWidget(accounts_list)
        form_layout.addWidget(QLabel("Targets (one per line):"))
        targets_input = QTextEdit()
        targets_input.setMaximumHeight(100)
        form_layout.addWidget(targets_input)
        form_layout.addWidget(QLabel("Message:"))
        message_input = QTextEdit()
        form_layout.addWidget(message_input)
        form_layout.addWidget(QLabel("Or use Template:"))
        template_combo = QComboBox()
        template_combo.addItem("None", None)
        try:
            templates = self.data.get_templates()
            for t in templates:
                template_combo.addItem(t.get('name'), t.get('id'))
        except:
            pass
        form_layout.addWidget(template_combo)
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
        auto_retry = QCheckBox("Auto Retry")
        form_layout.addWidget(auto_retry)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        buttons = QHBoxLayout()
        save_btn = QPushButton("Create")
        save_btn.setProperty("primary", True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        def save():
            selected = accounts_list.selectedItems()
            account_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected]
            targets_text = targets_input.toPlainText().strip()
            targets = [t.strip() for t in targets_text.split('\n') if t.strip()]
            data = {
                "name": name_input.text(),
                "account_ids": account_ids,
                "targets": targets,
                "message_text": message_input.toPlainText(),
                "template_id": template_combo.currentData(),
                "delay_min": delay_min.value(),
                "delay_max": delay_max.value(),
                "rotate_accounts": rotate_accounts.isChecked(),
                "auto_retry": auto_retry.isChecked()
            }
            try:
                self.data.create_campaign(data)
                toast_success("Campaign created!")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to create: {e}")
        save_btn.clicked.connect(save)
        dialog.exec()

    def run_campaign(self, campaign: Campaign):
        """Run campaign and show live dashboard"""
        try:
            self.data.update_campaign(campaign.id, {"status": "running"})
            toast_success(f"Campaign '{campaign.name}' started")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Failed to run: {e}")

    def edit_campaign(self, campaign: Campaign):
        toast_info("Edit functionality - implement as needed")

    def pause_campaign(self, campaign: Campaign):
        """Pause a running campaign"""
        try:
            self.data.update_campaign(campaign.id, {"status": "paused"})
            toast_info(f"Campaign '{campaign.name}' paused")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Failed to pause: {e}")

    def schedule_campaign(self, campaign: Campaign):
        """Schedule a draft campaign"""
        try:
            self.data.update_campaign(campaign.id, {"status": "scheduled"})
            toast_success(f"Campaign '{campaign.name}' scheduled")
            self.fetch_data()
        except Exception as e:
            toast_error(f"Failed to schedule: {e}")

    def rerun_campaign(self, campaign: Campaign):
        """Re-run a completed/failed campaign"""
        reply = QMessageBox.question(
            self, 
            "Re-run Campaign", 
            f'Re-run campaign "{campaign.name}"?\n\nThis will send messages to all targets again.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.update_campaign(campaign.id, {"status": "running"})
                toast_success(f"Campaign '{campaign.name}' re-started")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to re-run: {e}")

    def delete_campaign(self, campaign: Campaign):
        reply = QMessageBox.question(self, "Delete Campaign", f"Delete '{campaign.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
        
        # Enhanced Title with icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        
        title_icon = QLabel("🔍")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        
        title = QLabel("Scraper")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
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
                background-color: rgba(31, 111, 235, 0.2);
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
            # TODO: Implement scraper service method
            toast_info("Scraper functionality needs to be implemented in service manager")
        except Exception as e:
            toast_error(f"Failed to start scrape: {e}")

    def poll_scrape_job(self, job_id: str):
        try:
            status = self.data.get_job_status(job_id)
            job_status = status.get("status", "unknown")
            self.scrape_status.setText(f"Status: {job_status}")
            if job_status == "completed":
                toast_success("Scraping completed")
            elif job_status == "failed":
                toast_error(f"Scraping failed: {status.get('message', 'Unknown error')}")
            else:
                QTimer.singleShot(2000, lambda: self.poll_scrape_job(job_id))
        except Exception as e:
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
        text = '\n'.join(usernames)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        toast_success(f"Copied {len(usernames)} usernames to clipboard")

    def start_join(self):
        selected = self.join_accounts_list.selectedItems()
        if not selected:
            toast_warning("Please select at least one account")
            return
        account_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected]
        groups_text = self.join_groups_input.toPlainText().strip()
        if not groups_text:
            toast_warning("Please enter at least one group")
            return
        groups = [g.strip() for g in groups_text.split('\n') if g.strip()]
        try:
            # TODO: Implement join groups in service manager
            toast_info("Join groups functionality needs to be implemented")
        except Exception as e:
            toast_error(f"Failed to start join: {e}")


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
        # Enhanced Header with icon
        header = QHBoxLayout()
        
        title_icon = QLabel("🌐")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        
        title = QLabel("Proxies")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
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
        self.table.setColumnWidth(4, 70)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 120)
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
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31, 111, 235, 0.2);
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
            data = self.data.get_proxies()
            self.proxies = [Proxy.from_dict(p) for p in data]
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
            if proxy.is_active:
                status_item.setForeground(QColor(COLORS['accent_green']))
            else:
                status_item.setForeground(QColor(COLORS['accent_red']))
            self.table.setItem(row, 4, status_item)
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(3)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            test_btn = QPushButton("Test")
            test_btn.setFixedSize(47, 26)
            test_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_blue']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 2px 6px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD);
                }}
            """)
            test_btn.clicked.connect(lambda _, p=proxy: self.test_proxy(p))
            actions_layout.addWidget(test_btn)
            
            delete_btn = QPushButton("Del")
            delete_btn.setFixedSize(42, 26)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_red']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 2px 6px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7B72, stop:1 #F85149);
                }}
            """)
            delete_btn.clicked.connect(lambda _, p=proxy: self.delete_proxy(p))
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 36)

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
            data = {
                "scheme": scheme_combo.currentText(),
                "host": host_input.text(),
                "port": port_input.value(),
                "username": username_input.text() or None,
                "password": password_input.text() or None
            }
            try:
                self.data.create_proxy(data)
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
            try:
                # TODO: Implement bulk import in service manager
                toast_info("Bulk import needs to be implemented")
                dialog.accept()
                self.fetch_data()
            except Exception as e:
                toast_error(f"Import failed: {e}")
        import_btn.clicked.connect(do_import)
        dialog.exec()

    def test_proxy(self, proxy: Proxy):
        try:
            # TODO: Implement proxy test in service manager
            toast_info("Proxy test needs to be implemented")
        except Exception as e:
            toast_error(f"Proxy test failed: {e}")

    def delete_proxy(self, proxy: Proxy):
        reply = QMessageBox.question(self, "Delete Proxy", f"Delete proxy {proxy.host}:{proxy.port}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_proxy(proxy.id)
                toast_success("Proxy deleted")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed to delete: {e}")


class TemplateBuilderDialog(QDialog):
    """Drag-and-drop style template builder dialog"""
    def __init__(self, parent=None, template=None, api_client=None):
        super().__init__(parent)
        self.data = api_client or data_service
        self.template = template
        self.builder_elements = []
        self.editing_template = template
        self.uploading = False
        
        self.setWindowTitle("Template Builder")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_secondary']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px;
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {COLORS['accent_blue']};
            }}
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 16px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
            }}
            QPushButton#primary {{
                background-color: {COLORS['accent_green']};
                border: none;
                color: {COLORS['text_inverse']};
            }}
            QPushButton#primary:hover {{
                background-color: {COLORS['accent_green_dark']};
            }}
            QPushButton#tool {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                text-align: left;
                padding: 12px;
            }}
            QPushButton#tool:hover {{
                background-color: {COLORS['bg_hover']};
                border: 1px solid {COLORS['accent_blue']};
            }}
            QScrollArea {{
                border: 2px dashed {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['bg_primary']};
            }}
        """)
        
        self.init_ui()
        
        # Load existing template if editing
        if template:
            self.load_template(template)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Header with name input
        header = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Template Name (e.g., Welcome Message)" if not self.editing_template else "Edit template name...")
        header.addWidget(self.name_input, stretch=1)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 20px;
                color: {COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        layout.addLayout(header)
        
        # Main content area
        content = QHBoxLayout()
        
        # Toolbox (left side)
        toolbox = QVBoxLayout()
        toolbox_label = QLabel("Elements")
        toolbox_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_secondary']};")
        toolbox.addWidget(toolbox_label)
        
        tools = [
            ("📝 Text", "text"),
            ("🖼️ Photo", "photo"),
            ("🎥 Video", "video"),
            ("🎵 Audio", "audio"),
            ("📄 Document", "document"),
        ]
        
        for icon_label, element_type in tools:
            btn = QPushButton(f"  {icon_label}")
            btn.setObjectName("tool")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, t=element_type: self.add_element(t))
            toolbox.addWidget(btn)
        
        toolbox.addStretch()
        content.addLayout(toolbox, stretch=0)
        
        # Canvas area (right side)
        canvas_container = QVBoxLayout()
        
        self.canvas_widget = QWidget()
        self.canvas_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_primary']};
                border: 2px dashed {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        self.canvas_layout.setSpacing(8)
        self.canvas_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.empty_label = QLabel("Click elements on the left to add them to your template")
        self.empty_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 40px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_layout.addWidget(self.empty_label)
        
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidget(self.canvas_widget)
        canvas_scroll.setWidgetResizable(True)
        canvas_scroll.setMinimumHeight(400)
        
        canvas_container.addWidget(canvas_scroll)
        content.addLayout(canvas_container, stretch=1)
        
        layout.addLayout(content, stretch=1)
        
        # Bottom bar
        bottom = QHBoxLayout()
        self.elements_count = QLabel("0 elements")
        self.elements_count.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bottom.addWidget(self.elements_count)
        bottom.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(cancel_btn)
        
        self.save_btn = QPushButton("Create Template" if not self.editing_template else "Update Template")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.save_template)
        bottom.addWidget(self.save_btn)
        
        layout.addLayout(bottom)
    
    def load_template(self, template):
        """Load existing template for editing"""
        self.name_input.setText(template.name)
        
        # Add text element if exists
        if template.text:
            self.add_element('text', content=template.text)
        
        # Add media element if exists
        if template.media_path and template.media_type:
            self.add_element(template.media_type, content=template.media_path, is_existing=True)
    
    def add_element(self, element_type, content='', is_existing=False):
        """Add a new element to the builder"""
        # Remove empty label if present
        if self.empty_label:
            self.empty_label.hide()
        
        element_id = len(self.builder_elements)
        
        # Create element widget
        element_widget = QWidget()
        element_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        element_layout = QHBoxLayout(element_widget)
        element_layout.setSpacing(8)
        
        # Element type label
        type_icons = {
            'text': '📝 Text',
            'photo': '🖼️ Photo',
            'video': '🎥 Video',
            'audio': '🎵 Audio',
            'document': '📄 Doc'
        }
        type_label = QLabel(type_icons.get(element_type, element_type))
        type_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        type_label.setFixedWidth(60)
        element_layout.addWidget(type_label)
        
        # Content area
        if element_type == 'text':
            content_widget = QTextEdit()
            content_widget.setPlainText(content)
            content_widget.setPlaceholderText("Type your message here...\n\nTips:\n• Use {name} for recipient's name\n• Use {target} for username")
            content_widget.setMinimumHeight(80)
            content_widget.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {COLORS['bg_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 8px;
                    color: {COLORS['text_primary']};
                }}
            """)
            element_layout.addWidget(content_widget, stretch=1)
        else:
            # Media element
            media_container = QFrame()
            media_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_primary']};
                    border: 2px {'solid' if content else 'dashed'} {COLORS['border']};
                    border-radius: 6px;
                    padding: 8px;
                }}
                QFrame:hover {{
                    border: 2px solid {COLORS['accent_blue']};
                }}
            """)
            media_layout = QHBoxLayout(media_container)
            media_layout.setContentsMargins(8, 8, 8, 8)
            
            if content:
                # Show existing file
                file_label = QLabel(f"✓ {os.path.basename(content) if isinstance(content, str) else content.name if hasattr(content, 'name') else str(content)}")
                file_label.setStyleSheet(f"color: {COLORS['accent_green']};")
                media_layout.addWidget(file_label)
            else:
                # Show upload prompt
                upload_label = QLabel(f"📁 Click to upload {element_type} or drag & drop")
                upload_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
                media_layout.addWidget(upload_label)
                
                # Make clickable to upload
                media_container.mousePressEvent = lambda _, t=element_type, e=element_id: self.select_media_file(t, e)
            
            element_layout.addWidget(media_container, stretch=1)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLORS['text_muted']};
                font-size: 16px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent_red']};
            }}
        """)
        remove_btn.clicked.connect(lambda _, w=element_widget, e=element_id: self.remove_element(w, e))
        element_layout.addWidget(remove_btn)
        
        # Store element data
        element_data = {
            'id': element_id,
            'type': element_type,
            'widget': content_widget if element_type == 'text' else media_container,
            'content': content,
            'is_existing': is_existing
        }
        self.builder_elements.append(element_data)
        
        self.canvas_layout.addWidget(element_widget)
        self.update_count()
    
    def select_media_file(self, media_type, element_id):
        """Open file dialog to select media file"""
        filters = {
            'photo': "Images (*.png *.jpg *.jpeg *.gif *.webp)",
            'video': "Videos (*.mp4 *.avi *.mov *.mkv *.webm)",
            'audio': "Audio (*.mp3 *.ogg *.wav *.flac *.m4a)",
            'document': "All Files (*)"
        }
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            f"Select {media_type.capitalize()} File", 
            "", 
            filters.get(media_type, "All Files (*)")
        )
        
        if file_path:
            # Update element
            for el in self.builder_elements:
                if el['id'] == element_id:
                    el['content'] = file_path
                    el['is_existing'] = False
                    # Update UI
                    container = el['widget']
                    # Clear layout and add new label
                    while container.layout().count():
                        item = container.layout().takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    file_label = QLabel(f"✓ {os.path.basename(file_path)}")
                    file_label.setStyleSheet(f"color: {COLORS['accent_green']};")
                    container.layout().addWidget(file_label)
                    break
            
            toast_success(f"Selected: {os.path.basename(file_path)}")
    
    def remove_element(self, widget, element_id):
        """Remove an element from the builder"""
        widget.deleteLater()
        self.builder_elements = [e for e in self.builder_elements if e['id'] != element_id]
        
        # Show empty label if no elements
        if not self.builder_elements and self.empty_label:
            self.empty_label.show()
        
        self.update_count()
    
    def update_count(self):
        """Update the elements count label"""
        count = len(self.builder_elements)
        self.elements_count.setText(f"{count} element{'s' if count != 1 else ''}")
    
    def save_template(self):
        """Save the template from builder elements"""
        template_name = self.name_input.text().strip()
        if not template_name:
            toast_error("Please enter a template name")
            return
        
        if not self.builder_elements:
            toast_error("Please add at least one element")
            return
        
        self.uploading = True
        self.save_btn.setEnabled(False)
        self.save_btn.setText("Saving...")
        
        try:
            # Process elements
            combined_text = ""
            media_path = ""
            media_type = ""
            
            for el in self.builder_elements:
                if el['type'] == 'text':
                    text_content = el['widget'].toPlainText().strip()
                    if text_content:
                        if combined_text:
                            combined_text += "\n" + text_content
                        else:
                            combined_text = text_content
                elif el['type'] in ['photo', 'video', 'audio', 'document']:
                    # Handle media
                    content = el['content']
                    if content and not media_path:  # Only use first media
                        if isinstance(content, str) and os.path.exists(content):
                            # New file to upload
                            with open(content, 'rb') as f:
                                import requests
                                files = {'file': (os.path.basename(content), f)}
                                res = requests.post(f"{API_BASE_URL}/templates/upload", files=files)
                                if res.status_code == 200:
                                    result = res.json()
                                    media_path = result.get('filename', '')
                                    media_type = result.get('media_type', el['type'])
                                else:
                                    toast_error(f"Failed to upload media: {res.text}")
                                    return
                        elif el.get('is_existing'):
                            # Keep existing media
                            media_path = content
                            media_type = el['type']
            
            # Build payload
            payload = {
                "name": template_name,
                "text": combined_text,
                "media_path": media_path or None,
                "media_type": media_type or None
            }
            
            if self.editing_template:
                self.data.update_template(self.editing_template.id, payload)
                toast_success("Template updated successfully!")
            else:
                self.data.create_template(payload)
                toast_success("Template created successfully!")
            
            self.accept()
            
        except Exception as e:
            toast_error(f"Failed to save: {str(e)}")
        finally:
            self.uploading = False
            self.save_btn.setEnabled(True)
            self.save_btn.setText("Update Template" if self.editing_template else "Create Template")


class TemplatesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.templates = []
        self.init_ui()
        self.fetch_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        # Enhanced Header with icon
        header = QHBoxLayout()
        
        title_icon = QLabel("📝")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        
        title = QLabel("Message Templates")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
        header.addWidget(title)
        header.addStretch()
        self.create_btn = QPushButton("+ Create Template")
        self.create_btn.setProperty("primary", True)
        self.create_btn.clicked.connect(self.create_template)
        header.addWidget(self.create_btn)
        layout.addLayout(header)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Text Preview", "Media", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 150)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 120)
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
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(31, 111, 235, 0.2);
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
            data = self.data.get_templates()
            self.templates = [MessageTemplate.from_dict(t) for t in data]
            self.update_table()
        except Exception as e:
            toast_error(f"Failed to fetch templates: {e}")

    def update_table(self):
        self.table.setRowCount(len(self.templates))
        for row, template in enumerate(self.templates):
            self.table.setItem(row, 0, QTableWidgetItem(template.name))
            preview = template.text[:50] + "..." if len(template.text) > 50 else template.text
            self.table.setItem(row, 1, QTableWidgetItem(preview))
            media_text = f"{template.media_type}: {template.media_path}" if template.media_path else "None"
            self.table.setItem(row, 2, QTableWidgetItem(media_text))
            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(3)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(47, 26)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_blue']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 2px 6px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #79B8FF, stop:1 #388BFD);
                }}
            """)
            edit_btn.clicked.connect(lambda _, t=template: self.edit_template(t))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Del")
            delete_btn.setFixedSize(42, 26)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['gradient_red']};
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: 500;
                    font-size: 10px;
                    padding: 2px 6px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7B72, stop:1 #F85149);
                }}
            """)
            delete_btn.clicked.connect(lambda _, t=template: self.delete_template(t))
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 3, actions_widget)
            self.table.setRowHeight(row, 36)

    def create_template(self):
        dialog = TemplateBuilderDialog(self, api_client=self.data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.fetch_data()

    def edit_template(self, template: MessageTemplate):
        dialog = TemplateBuilderDialog(self, template=template, api_client=self.data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.fetch_data()

    def delete_template(self, template: MessageTemplate):
        reply = QMessageBox.question(self, "Delete Template", f"Delete '{template.name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_template(template.id)
                toast_success("Template deleted")
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
        # Enhanced Header with icon
        header = QHBoxLayout()
        
        title_icon = QLabel("📋")
        title_icon.setStyleSheet("font-size: 32px;")
        header.addWidget(title_icon)
        
        title = QLabel("Logs")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
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
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 70)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 140)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
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
                background-color: rgba(31, 111, 235, 0.2);
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

    def fetch_logs(self):
        limit = 200
        level = self.level_combo.currentText()
        category = self.category_combo.currentText()
        try:
            data = self.data.get_logs(category if category != "All" else None, limit)
            logs = [Log.from_dict(l) for l in data]
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
        reply = QMessageBox.question(self, "Clear Logs", "Clear all logs?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # TODO: Implement logs clear in service manager
                toast_info("Logs clear needs to be implemented")
                self.fetch_logs()
            except Exception as e:
                toast_error(f"Failed to clear: {e}")


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
        
        # Enhanced Title with icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 16)
        
        title_icon = QLabel("⚙️")
        title_icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(title_icon)
        
        title = QLabel("Settings")
        title.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding-left: 12px;
        """)
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
            "flood_wait_cap": self.flood_wait_cap.value()
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
            "Accounts": AccountsPage(),
            "Messaging": MessagingPage(),
            "Campaigns": CampaignsPage(),
            "Scraper": ScraperPage(),
            "Proxies": ProxiesPage(),
            "Templates": TemplatesPage(),
            "Logs": LogsPage(),
            "Settings": SettingsPage(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_frame, 1)
        self.sidebar = Sidebar(self.navigate)
        main_layout.insertWidget(0, self.sidebar)
        init_toast_manager(self)
        # DataService doesn't have error/success signals like old APIClient
        # Toast notifications are handled directly in UI methods
        self.backend_timer = QTimer()
        self.backend_timer.timeout.connect(self.check_backend)
        self.backend_timer.start(10000)
        self.navigate("Dashboard")

    def navigate(self, page_name):
        if page_name in self.pages:
            index = list(self.pages.keys()).index(page_name)
            self.stack.setCurrentIndex(index)
            for name, btn in self.sidebar.buttons.items():
                btn.set_active(name == page_name)

    def check_backend(self):
        # Backend is now integrated, no need for health check
        pass


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

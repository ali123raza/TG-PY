"""
Campaign Live Dashboard Dialog - Shows real-time campaign progress
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QGridLayout, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from toast import toast_success, toast_error, toast_info
from api_client import get_api_client, Endpoints


# Color palette (same as main.py)
COLORS = {
    'bg_primary': '#0D1117',
    'bg_secondary': '#161B22',
    'bg_tertiary': '#21262D',
    'text_primary': '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted': '#6E7681',
    'border': '#30363D',
    'accent_blue': '#58A6FF',
    'accent_green': '#3FB950',
    'accent_red': '#F85149',
    'accent_yellow': '#D29922',
}


class CampaignLiveDialog(QDialog):
    """Live campaign progress dashboard matching React frontend"""
    
    campaign_completed = pyqtSignal()
    
    def __init__(self, parent=None, job_id: str = "", api_client=None):
        super().__init__(parent)
        self.api = api_client or get_api_client()
        self.job_id = job_id
        self.live_stats = None
        self.poll_timer = None
        
        self.setWindowTitle("Live Campaign Progress")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border-radius: 8px;
            }}
        """)
        
        self.setup_ui()
        self.start_polling()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header with status indicator
        header = QHBoxLayout()
        
        # Pulsing status indicator
        self.status_container = QFrame()
        self.status_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"""
            color: {COLORS['accent_blue']};
            font-size: 14px;
        """)
        status_layout.addWidget(self.status_dot)
        
        self.status_label = QLabel("RUNNING")
        self.status_label.setStyleSheet(f"""
            color: {COLORS['accent_blue']};
            font-weight: bold;
            font-size: 14px;
        """)
        status_layout.addWidget(self.status_label)
        
        header.addWidget(self.status_container)
        header.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 24px;
                color: {COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
            }}
        """)
        close_btn.clicked.connect(self.close_dialog)
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Progress section
        progress_frame = QFrame()
        progress_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        progress_layout = QVBoxLayout(progress_frame)
        
        # Progress header
        progress_header = QHBoxLayout()
        progress_header.addWidget(QLabel("Progress"))
        self.progress_text = QLabel("0 / 0")
        self.progress_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        progress_header.addWidget(self.progress_text)
        progress_layout.addLayout(progress_header)
        
        # Stacked progress bar (green for sent, red for failed)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_tertiary']};
                border-radius: 8px;
                height: 16px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent_green']};
                border-radius: 8px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_frame)
        
        # Stats grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        
        # Sent stat
        sent_frame = self.create_stat_card("Sent", "0", COLORS['accent_blue'])
        stats_grid.addWidget(sent_frame, 0, 0)
        
        # Failed stat
        failed_frame = self.create_stat_card("Failed", "0", COLORS['accent_red'])
        stats_grid.addWidget(failed_frame, 0, 1)
        
        # Total stat
        total_frame = self.create_stat_card("Total", "0", COLORS['text_secondary'])
        stats_grid.addWidget(total_frame, 0, 2)
        
        layout.addLayout(stats_grid)
        
        # Recent Activity
        activity_label = QLabel("Recent Activity")
        activity_label.setStyleSheet(f"""
            font-weight: 600;
            color: {COLORS['text_secondary']};
            margin-top: 8px;
        """)
        layout.addWidget(activity_label)
        
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                max-height: 200px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                color: {COLORS['accent_green']};
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.activity_list)
        
        # Cancel button (shown only when running)
        self.cancel_btn = QPushButton("Cancel Campaign")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_red']};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: white;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #FF6B6B;
            }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_campaign)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
    
    def create_stat_card(self, label: str, value: str, color: str):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: bold;
            color: {color};
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        
        name_label = QLabel(label)
        name_label.setStyleSheet(f"""
            font-size: 12px;
            color: {COLORS['text_muted']};
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Store reference for updates
        setattr(self, f"{label.lower()}_value", value_label)
        
        return frame
    
    def start_polling(self):
        """Start polling for campaign status"""
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_status)
        self.poll_timer.start(1000)  # Poll every second
        self.poll_status()  # First poll immediately
    
    def poll_status(self):
        """Fetch campaign status from API"""
        try:
            status = self.api.get(f"/messaging/jobs/{self.job_id}")
            self.update_display(status)
            
            # Check if completed
            if status.get('status') in ['completed', 'failed', 'cancelled']:
                self.poll_timer.stop()
                self.campaign_completed.emit()
                self.update_final_state(status.get('status'))
        except Exception as e:
            print(f"Poll error: {e}")
    
    def update_display(self, stats: dict):
        """Update UI with latest stats"""
        sent = stats.get('sent', 0)
        failed = stats.get('failed', 0)
        total = stats.get('total', 0)
        status = stats.get('status', 'unknown')
        
        # Update progress
        if total > 0:
            progress = int(((sent + failed) / total) * 100)
            self.progress_bar.setValue(progress)
            self.progress_text.setText(f"{sent + failed} / {total}")
        
        # Update stat cards
        self.sent_value.setText(str(sent))
        self.failed_value.setText(str(failed))
        self.total_value.setText(str(total))
        
        # Update status
        status_colors = {
            'running': COLORS['accent_blue'],
            'completed': COLORS['accent_green'],
            'failed': COLORS['accent_red'],
            'cancelled': COLORS['text_muted']
        }
        color = status_colors.get(status, COLORS['text_muted'])
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        
        # Update activity list (recent sends)
        current_count = self.activity_list.count()
        if sent > current_count:
            for i in range(current_count + 1, min(sent + 1, current_count + 6)):
                item = QListWidgetItem(f"✓ Message sent to recipient #{i}")
                self.activity_list.insertItem(0, item)
    
    def update_final_state(self, status: str):
        """Update UI when campaign ends"""
        self.cancel_btn.setVisible(False)
        
        if status == 'completed':
            self.status_label.setText("COMPLETED")
            self.status_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: bold;")
            toast_success("Campaign completed!")
        elif status == 'failed':
            self.status_label.setText("FAILED")
            self.status_label.setStyleSheet(f"color: {COLORS['accent_red']}; font-weight: bold;")
            toast_error("Campaign failed")
        elif status == 'cancelled':
            self.status_label.setText("CANCELLED")
            self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
            toast_info("Campaign cancelled")
    
    def cancel_campaign(self):
        """Cancel the running campaign"""
        try:
            self.api.post(f"/messaging/jobs/{self.job_id}/cancel")
            toast_info("Cancelling campaign...")
        except Exception as e:
            toast_error(f"Failed to cancel: {e}")
    
    def close_dialog(self):
        """Close the dialog"""
        if self.poll_timer:
            self.poll_timer.stop()
        self.reject()
    
    def closeEvent(self, event):
        """Clean up on close"""
        if self.poll_timer:
            self.poll_timer.stop()
        event.accept()

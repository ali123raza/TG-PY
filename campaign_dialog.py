"""
Campaign Live Dashboard Dialog – shows real-time campaign progress.

FIX: Replaced api_client (HTTP) with data_service (direct service calls).
The old code polled /messaging/jobs/{job_id} via HTTP; with no server running
in unified mode every poll silently swallowed a ConnectionError.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QGridLayout, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from toast import toast_success, toast_error, toast_info
from data_service import get_data_service

COLORS = {
    'bg_primary':     '#0D1117',
    'bg_secondary':   '#161B22',
    'bg_tertiary':    '#21262D',
    'text_primary':   '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted':     '#6E7681',
    'border':         '#30363D',
    'accent_blue':    '#58A6FF',
    'accent_green':   '#3FB950',
    'accent_red':     '#F85149',
    'accent_yellow':  '#D29922',
}


class CampaignLiveDialog(QDialog):
    """Live campaign progress dashboard."""

    campaign_completed = pyqtSignal()

    def __init__(self, parent=None, job_id: str = "", api_client=None):
        super().__init__(parent)
        # FIX: accept either a DataService or fall back to the singleton
        self.data = api_client or get_data_service()
        self.job_id = job_id
        self.poll_timer: QTimer | None = None

        self.setWindowTitle("Live Campaign Progress")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QLabel {{ color: {COLORS['text_primary']}; }}
            QFrame {{
                background-color: {COLORS['bg_tertiary']};
                border-radius: 8px;
            }}
        """)
        self.setup_ui()
        self.start_polling()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        status_row = QFrame()
        status_row.setStyleSheet("QFrame { background-color: transparent; }")
        sl = QHBoxLayout(status_row)
        sl.setContentsMargins(0, 0, 0, 0)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {COLORS['accent_blue']}; font-size: 14px;")
        sl.addWidget(self.status_dot)
        self.status_label = QLabel("RUNNING")
        self.status_label.setStyleSheet(f"color: {COLORS['accent_blue']}; font-weight: bold; font-size: 14px;")
        sl.addWidget(self.status_label)
        header.addWidget(status_row)
        header.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; font-size: 24px; color: {COLORS['text_secondary']}; }}
            QPushButton:hover {{ color: {COLORS['text_primary']}; }}
        """)
        close_btn.clicked.connect(self.close_dialog)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Progress
        progress_frame = QFrame()
        progress_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        pl = QVBoxLayout(progress_frame)
        ph = QHBoxLayout()
        ph.addWidget(QLabel("Progress"))
        self.progress_text = QLabel("0 / 0")
        self.progress_text.setStyleSheet(f"color: {COLORS['text_secondary']};")
        ph.addWidget(self.progress_text)
        pl.addLayout(ph)

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
            QProgressBar::chunk {{ background-color: {COLORS['accent_green']}; border-radius: 8px; }}
        """)
        pl.addWidget(self.progress_bar)
        layout.addWidget(progress_frame)

        # Stats cards
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self._make_stat_card("Sent",   "0", COLORS['accent_blue']),  0, 0)
        grid.addWidget(self._make_stat_card("Failed", "0", COLORS['accent_red']),   0, 1)
        grid.addWidget(self._make_stat_card("Total",  "0", COLORS['text_secondary']), 0, 2)
        layout.addLayout(grid)

        # Activity list
        activity_lbl = QLabel("Recent Activity")
        activity_lbl.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']}; margin-top: 8px;")
        layout.addWidget(activity_lbl)

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

        # Cancel button
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
            QPushButton:hover {{ background-color: #FF6B6B; }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_campaign)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def _make_stat_card(self, label: str, value: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        fl = QVBoxLayout(frame)
        fl.setSpacing(8)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(val_lbl)

        name_lbl = QLabel(label)
        name_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']};")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fl.addWidget(name_lbl)

        setattr(self, f"{label.lower()}_value", val_lbl)
        return frame

    # ------------------------------------------------------------------
    # Polling – FIX: use data_service.get_job_status() not HTTP GET
    # ------------------------------------------------------------------

    def start_polling(self):
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_status)
        self.poll_timer.start(1000)
        self.poll_status()

    def poll_status(self):
        """Fetch job status via data_service (direct call, no HTTP)."""
        if not self.job_id:
            return
        try:
            # FIX: was self.api.get(f"/messaging/jobs/{self.job_id}")
            status = self.data.get_job_status(self.job_id)
            if status is None:
                # Job not found — may be a messaging job not tracked by service_manager yet
                return
            self.update_display(status)
            if status.get('status') in ('completed', 'failed', 'cancelled'):
                self.poll_timer.stop()
                self.campaign_completed.emit()
                self.update_final_state(status.get('status', 'unknown'))
        except Exception as exc:
            print(f"Poll error: {exc}")

    def update_display(self, stats: dict):
        sent   = stats.get('sent', 0)
        failed = stats.get('failed', 0)
        total  = stats.get('total', 0)
        status = stats.get('status', 'unknown')

        if total > 0:
            self.progress_bar.setValue(int((sent + failed) / total * 100))
            self.progress_text.setText(f"{sent + failed} / {total}")

        self.sent_value.setText(str(sent))
        self.failed_value.setText(str(failed))
        self.total_value.setText(str(total))

        color_map = {
            'running':   COLORS['accent_blue'],
            'completed': COLORS['accent_green'],
            'failed':    COLORS['accent_red'],
            'cancelled': COLORS['text_muted'],
        }
        color = color_map.get(status, COLORS['text_muted'])
        style = f"color: {color}; font-weight: bold; font-size: 14px;"
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(style)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 14px;")

        current_count = self.activity_list.count()
        if sent > current_count:
            for i in range(current_count + 1, min(sent + 1, current_count + 6)):
                self.activity_list.insertItem(0, QListWidgetItem(f"✓ Message sent to recipient #{i}"))

    def update_final_state(self, status: str):
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
        """Cancel the running campaign job."""
        if not self.job_id:
            return
        try:
            self.data.cancel_job(self.job_id)
            toast_info("Cancelling campaign…")
            self.cancel_btn.setEnabled(False)
        except Exception as exc:
            toast_error(f"Failed to cancel: {exc}")

    def close_dialog(self):
        if self.poll_timer:
            self.poll_timer.stop()
        self.reject()

    def closeEvent(self, event):
        if self.poll_timer:
            self.poll_timer.stop()
        event.accept()

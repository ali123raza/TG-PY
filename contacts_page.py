"""
Contacts Management Page
Peers (audience groups) + bulk import/export + status tracking
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QLineEdit, QTextEdit, QComboBox, QFileDialog,
    QMessageBox, QProgressBar, QSplitter, QColorDialog, QInputDialog,
    QAbstractItemView, QApplication, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from data_service import get_data_service
from toast import toast_success, toast_error, toast_info, toast_warning

data_service = get_data_service()

COLORS = {
    'bg_primary':     '#0D1117',
    'bg_secondary':   '#161B22',
    'bg_tertiary':    '#21262D',
    'bg_hover':       '#30363D',
    'text_primary':   '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted':     '#6E7681',
    'border':         '#30363D',
    'border_light':   '#21262D',
    'accent_blue':    '#58A6FF',
    'accent_blue_dark':'#1F6FEB',
    'accent_green':   '#3FB950',
    'accent_red':     '#F85149',
    'accent_yellow':  '#D29922',
    'gradient_blue':  'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #58A6FF,stop:1 #1F6FEB)',
    'gradient_green': 'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3FB950,stop:1 #238636)',
    'gradient_red':   'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F85149,stop:1 #DA3633)',
}

PEER_COLORS = [
    "#58A6FF", "#3FB950", "#F85149", "#D29922",
    "#A371F7", "#F778BA", "#39CFCF", "#FF8C42",
]


def _action_btn(label, gradient, hover, callback, width=None):
    b = QPushButton(label)
    b.setFixedHeight(30)
    if width:
        b.setFixedWidth(width)
    else:
        b.setMinimumWidth(60)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background: {gradient};
            border: none; border-radius: 6px;
            color: white; font-weight: 600; font-size: 11px;
            padding: 0px 10px;
        }}
        QPushButton:hover {{ background: {hover}; }}
    """)
    b.clicked.connect(callback)
    return b


# ─────────────────────────────────────────────────────────────────────────────
# Peer List Item (left panel)
# ─────────────────────────────────────────────────────────────────────────────

class PeerListItem(QFrame):
    clicked = pyqtSignal(int)  # peer_id

    def __init__(self, peer: dict, parent=None):
        super().__init__(parent)
        self.peer_id = peer["id"]
        self._selected = False
        self.setFixedHeight(62)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Color dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {peer.get('color', '#58A6FF')}; font-size: 16px;")
        dot.setFixedWidth(20)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dot)

        # Title + count
        info = QVBoxLayout()
        info.setSpacing(2)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter) # FIX: Center text vertically
        
        title_lbl = QLabel(peer["title"])
        title_lbl.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 13px;")
        count_lbl = QLabel(f"{peer.get('contact_count', 0):,} contacts")
        count_lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px;")
        
        info.addWidget(title_lbl)
        info.addWidget(count_lbl)
        layout.addLayout(info)
        layout.addStretch()

    def _update_style(self, selected: bool):
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background: rgba(31,111,235,0.15);
                    border-left: 3px solid {COLORS['accent_blue']};
                    border-radius: 6px;
                    margin: 0px 4px; /* FIX: Added margin so it doesn't touch sides */
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border-left: 3px solid transparent;
                    border-radius: 6px;
                    margin: 0px 4px; /* FIX */
                }}
                QFrame:hover {{
                    background: {COLORS['bg_hover']};
                    border-left: 3px solid {COLORS['border']};
                }}
            """)

    def set_selected(self, sel: bool):
        self._selected = sel
        self._update_style(sel)

    def mousePressEvent(self, event):
        self.clicked.emit(self.peer_id)


# ─────────────────────────────────────────────────────────────────────────────
# Import Dialog
# ─────────────────────────────────────────────────────────────────────────────

class ImportContactsDialog(QDialog):
    def __init__(self, peer: dict, parent=None):
        super().__init__(parent)
        self.peer = peer
        self.setWindowTitle(f"Import Contacts — {peer['title']}")
        self.setMinimumSize(560, 520)
        # FIX: Force modal dialog with solid background
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(f"""
            QDialog {{ 
                background-color: {COLORS['bg_secondary']}; 
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
            }}
            QLabel  {{ color: {COLORS['text_primary']}; }}
            QTextEdit, QComboBox {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px;
                color: {COLORS['text_primary']}; font-size: 13px;
            }}
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 16px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{ background-color: {COLORS['bg_hover']}; }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        hdr = QLabel(f"📥  Import into  <b>{self.peer['title']}</b>")
        hdr.setStyleSheet(f"font-size: 16px; color: {COLORS['text_primary']};")
        layout.addWidget(hdr)

        # Format hint
        hint = QLabel(
            "Supported formats — one per line:\n"
            "  +923001234567   (phone with +)\n"
            "  923001234567    (phone without +)\n"
            "  @username       (Telegram username)\n"
            "  123456789       (Telegram user_id)\n"
            "  +923001234567, Ahmed Ali   (phone, name CSV)"
        )
        hint.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"background: {COLORS['bg_primary']}; border-radius: 6px; padding: 10px;")
        layout.addWidget(hint)

        # Text area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText(
            "+923001111111\n+923002222222\n@username123\n...")
        self.text_area.setMinimumHeight(160)
        layout.addWidget(self.text_area)

        # OR — file import
        file_row = QHBoxLayout()
        file_btn = QPushButton("📂  Import from file (.txt / .csv)")
        file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        file_btn.clicked.connect(self._load_file)
        file_row.addWidget(file_btn)
        file_row.addStretch()
        layout.addLayout(file_row)

        # Preview count
        self.preview_lbl = QLabel("Paste contacts above")
        self.preview_lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(self.preview_lbl)
        self.text_area.textChanged.connect(self._update_preview)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        self.import_btn = _action_btn(
            "Import", COLORS['gradient_green'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #56D364,stop:1 #2EA043)",
            self._do_import, width=120)
        btn_row.addWidget(self.import_btn)
        layout.addLayout(btn_row)

    def _update_preview(self):
        text = self.text_area.toPlainText().strip()
        if not text:
            self.preview_lbl.setText("Paste contacts above")
            return
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        self.preview_lbl.setText(f"Preview: <b>{len(lines):,}</b> line(s) detected")

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Contacts File", "",
            "Text/CSV Files (*.txt *.csv);;All Files (*)")
        if path:
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    self.text_area.setPlainText(f.read())
                toast_info(f"Loaded: {os.path.basename(path)}")
            except Exception as e:
                toast_error(f"Could not read file: {e}")

    def _do_import(self):
        raw = self.text_area.toPlainText().strip()
        if not raw:
            toast_warning("No contacts to import")
            return
        self.import_btn.setEnabled(False)
        self.import_btn.setText("Importing…")
        try:
            result = data_service.bulk_import_contacts(self.peer["id"], raw)
            msg = (f"✓  Imported: {result['imported']:,}"
                   + (f"  |  Duplicates skipped: {result['duplicates']:,}"
                      if result["duplicates"] else ""))
            toast_success(msg)
            self.accept()
        except Exception as e:
            toast_error(f"Import failed: {e}")
        finally:
            self.import_btn.setEnabled(True)
            self.import_btn.setText("Import")


# ─────────────────────────────────────────────────────────────────────────────
# Peer Form Dialog (create / edit)
# ─────────────────────────────────────────────────────────────────────────────

class PeerDialog(QDialog):
    def __init__(self, peer: dict = None, parent=None):
        super().__init__(parent)
        self.peer = peer
        self.chosen_color = (peer["color"] if peer else PEER_COLORS[0])
        self.setWindowTitle("Edit Peer" if peer else "New Peer")
        self.setMinimumWidth(380)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_secondary']}; }}
            QLabel  {{ color: {COLORS['text_primary']}; font-size: 13px; }}
            QLineEdit, QTextEdit {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 12px;
                color: {COLORS['text_primary']}; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent_blue']}; }}
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 9px 18px;
                color: {COLORS['text_primary']}; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {COLORS['bg_hover']}; }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("Peer Title *"))
        self.title_input = QLineEdit(self.peer["title"] if self.peer else "")
        self.title_input.setPlaceholderText("e.g. Pakistan Leads 2025")
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Description (optional)"))
        self.desc_input = QLineEdit(self.peer.get("description", "") if self.peer else "")
        self.desc_input.setPlaceholderText("Short note about this peer")
        layout.addWidget(self.desc_input)

        # Color picker
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self.color_btn = QPushButton("  ●  Pick Color")
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setStyleSheet(
            self.color_btn.styleSheet() +
            f"color: {self.chosen_color}; font-size: 16px;")
        self.color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_btn)
        
        # Quick presets
        for c in PEER_COLORS[:6]:
            dot = QPushButton("●")
            dot.setFixedSize(28, 28)
            dot.setCursor(Qt.CursorShape.PointingHandCursor)
            dot.setStyleSheet(f"""
                QPushButton {{
                    color: {c}; font-size: 18px;
                    background: transparent; border: none; border-radius: 14px;
                }}
                QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
            """)
            dot.clicked.connect(lambda _, col=c: self._set_color(col))
            color_row.addWidget(dot)
        color_row.addStretch()
        layout.addLayout(color_row)

        # Buttons
        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        self.save_btn = _action_btn(
            "Save" if self.peer else "Create",
            COLORS['gradient_blue'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD)",
            self._save, width=100)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    def _pick_color(self):
        color = QColorDialog.getColor(
            QColor(self.chosen_color), self, "Pick Peer Color")
        if color.isValid():
            self._set_color(color.name())

    def _set_color(self, color: str):
        self.chosen_color = color
        self.color_btn.setStyleSheet(
            self.color_btn.styleSheet().split("color:")[0] +
            f"color: {color}; font-size: 16px;")

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            self.title_input.setStyleSheet(
                self.title_input.styleSheet() + "border-color: red;")
            return
        self._result = {
            "title": title,
            "description": self.desc_input.text().strip(),
            "color": self.chosen_color,
        }
        self.accept()

    def get_data(self) -> dict:
        return getattr(self, "_result", {})


# ─────────────────────────────────────────────────────────────────────────────
# Contacts Page
# ─────────────────────────────────────────────────────────────────────────────

class ContactsPage(QWidget):
    """
    Full Contacts Management page.
    Left panel: peer list.
    Right panel: contacts for selected peer.
    """
    peers_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.data = data_service
        self.peers: list[dict] = []
        self.current_peer: dict | None = None
        self.peer_widgets: dict[int, PeerListItem] = {}
        self._init_ui()
        self.refresh_peers()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Page header ───────────────────────────────────────────────────────
        header_widget = QWidget()
        header_widget.setFixedHeight(70)
        header_widget.setStyleSheet(
            f"background-color: {COLORS['bg_primary']}; "
            f"border-bottom: 1px solid {COLORS['border']};")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(24, 0, 24, 0)

        icon_lbl = QLabel("👥")
        icon_lbl.setStyleSheet("font-size: 26px; padding-right: 8px;")
        header_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Contacts")
        title_lbl.setStyleSheet(
            f"font-size: 26px; font-weight: bold; color: {COLORS['text_primary']};")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(32)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_secondary']};
                font-weight: 600; font-size: 12px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_blue_dark']};
                border-color: {COLORS['accent_blue']};
                color: white;
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_peers)
        header_layout.addWidget(refresh_btn)
        
        root.addWidget(header_widget)

        # ── Main splitter ─────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1) # FIX: Clean handle
        splitter.setStyleSheet(f"""
            QSplitter {{ border: none; }}
            QSplitter::handle {{ background: {COLORS['border']}; width: 1px; }}
        """)

        # LEFT — peer list
        left = QWidget()
        left.setMinimumWidth(230)
        left.setMaximumWidth(280)
        left.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_secondary']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 12, 10, 12)
        left_layout.setSpacing(6)

        peers_lbl = QLabel("PEERS")
        peers_lbl.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 0 4px 4px 4px;
        """)
        left_layout.addWidget(peers_lbl)

        new_peer_btn = QPushButton("＋  New Peer")
        new_peer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_peer_btn.setFixedHeight(36)
        new_peer_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['gradient_blue']};
                border: none; border-radius: 8px;
                color: white; font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD);
            }}
        """)
        new_peer_btn.clicked.connect(self._create_peer)
        left_layout.addWidget(new_peer_btn)

        peer_scroll = QScrollArea()
        peer_scroll.setWidgetResizable(True)
        peer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        peer_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_secondary']};
                width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['bg_hover']};
                border-radius: 3px; min-height: 20px;
            }}
        """)
        self.peers_container = QWidget()
        self.peers_container.setStyleSheet("background: transparent;")
        self.peers_layout = QVBoxLayout(self.peers_container)
        self.peers_layout.setContentsMargins(0, 4, 0, 4)
        self.peers_layout.setSpacing(3)
        self.peers_layout.addStretch()
        peer_scroll.setWidget(self.peers_container)
        left_layout.addWidget(peer_scroll)
        splitter.addWidget(left)

        # RIGHT — peer detail
        self.right_panel = QWidget()
        self.right_panel.setObjectName("RightPanel") # FIX: Prevent global borders
        self.right_panel.setStyleSheet(f"""
            QWidget#RightPanel {{
                background-color: {COLORS['bg_primary']};
                border: none;
            }}
        """)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(24, 20, 24, 16)
        self.right_layout.setSpacing(14)
        self._show_empty_state()
        splitter.addWidget(self.right_panel)
        splitter.setSizes([250, 950])

        root.addWidget(splitter)

    def _show_empty_state(self):
        self._clear_right()
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(container)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("👥")
        icon_lbl.setStyleSheet("font-size: 48px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(icon_lbl)

        msg_lbl = QLabel("No peer selected")
        msg_lbl.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: 600;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(msg_lbl)

        hint_lbl = QLabel("Create a peer using + New Peer  |  select one from the left")
        hint_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 13px;")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(hint_lbl)

        self.right_layout.addStretch()
        self.right_layout.addWidget(container)
        self.right_layout.addStretch()

    def _clear_right(self):
        """Clear all widgets from right panel, including nested layouts."""
        def clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widget.hide()  # Hide first
                    widget.setParent(None)  # Detach from parent
                    widget.deleteLater()
                elif item.layout():
                    clear_layout(item.layout())
        
        clear_layout(self.right_layout)

    # ── Peer List ─────────────────────────────────────────────────────────────

    def refresh_peers(self):
        try:
            self.peers = self.data.get_peers()
        except Exception as e:
            toast_error(f"Failed to load peers: {e}")
            self.peers = []

        for w in self.peer_widgets.values():
            w.deleteLater()
        self.peer_widgets.clear()

        while self.peers_layout.count() > 1:
            item = self.peers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for peer in self.peers:
            item = PeerListItem(peer)
            item.clicked.connect(self._select_peer)
            self.peer_widgets[peer["id"]] = item
            self.peers_layout.insertWidget(
                self.peers_layout.count() - 1, item)

        if self.current_peer:
            still = next(
                (p for p in self.peers if p["id"] == self.current_peer["id"]),
                None)
            if still:
                self.current_peer = still
                self._select_peer(still["id"])
            else:
                self.current_peer = None
                self._show_empty_state()

        self.peers_changed.emit()

    def _select_peer(self, peer_id: int):
        for w in self.peer_widgets.values():
            w.set_selected(False)
        if peer_id in self.peer_widgets:
            self.peer_widgets[peer_id].set_selected(True)

        peer = next((p for p in self.peers if p["id"] == peer_id), None)
        if peer:
            self.current_peer = peer
            self._build_peer_detail(peer)

    # ── Peer Detail Panel ─────────────────────────────────────────────────────

    def _build_peer_detail(self, peer: dict):
        self._clear_right()

        # ── Peer Header Card ─────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame#PeerHeaderCard {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        header_card.setObjectName("PeerHeaderCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {peer.get('color','#58A6FF')}; font-size: 20px;")
        title_row.addWidget(dot)

        peer_title = QLabel(peer["title"])
        peer_title.setStyleSheet(
            f"font-size: 22px; font-weight: bold; "
            f"color: {COLORS['text_primary']}; padding-left: 6px;")
        title_row.addWidget(peer_title)
        title_row.addStretch()

        edit_btn = _action_btn(
            "✏ Edit", COLORS['gradient_blue'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD)",
            lambda: self._edit_peer(peer))
        title_row.addWidget(edit_btn)

        del_btn = _action_btn(
            "✕ Delete", COLORS['gradient_red'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149)",
            lambda: self._delete_peer(peer))
        title_row.addWidget(del_btn)
        header_layout.addLayout(title_row)

        # Description (inside same card)
        if peer.get("description"):
            desc = QLabel(peer["description"])
            desc.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 13px; padding-left: 26px; padding-top: 4px;")
            desc.setWordWrap(True)
            header_layout.addWidget(desc)

        self.right_layout.addWidget(header_card)
        self.right_layout.addSpacing(16)  # Add space between header and stats

        # ── Stats bar ─────────────────────────────────────────────────────────
        try:
            counts = self.data.get_peer_contact_count(peer["id"])
        except Exception:
            counts = {}

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        stat_defs = [
            ("Total",   counts.get("total", 0),   COLORS['text_primary']),
            ("Pending", counts.get("pending", 0), COLORS['accent_yellow']),
            ("Sent",    counts.get("sent", 0),    COLORS['accent_green']),
            ("Failed",  counts.get("failed", 0),  COLORS['accent_red']),
            ("Invalid", counts.get("invalid", 0), COLORS['text_muted']),
        ]
        for label, count, color in stat_defs:
            card = QFrame()
            card.setObjectName(f"StatCard_{label}")
            card.setStyleSheet(f"""
                QFrame#StatCard_{label} {{
                    background-color: {COLORS['bg_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setSpacing(4)
            cl.setContentsMargins(16, 12, 16, 12)
            val_lbl = QLabel(f"{count:,}")
            val_lbl.setStyleSheet(
                f"font-size: 20px; font-weight: bold; color: {color};")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(
                f"font-size: 11px; color: {COLORS['text_muted']};")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val_lbl)
            cl.addWidget(name_lbl)
            stats_row.addWidget(card)
        stats_row.addStretch()
        self.right_layout.addLayout(stats_row)

        # ── Action buttons ────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        imp_btn = _action_btn(
            "📥 Import",
            COLORS['gradient_green'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #56D364,stop:1 #2EA043)",
            lambda: self._import_contacts(peer))
        action_row.addWidget(imp_btn)

        exp_txt_btn = _action_btn(
            "📤 Export TXT",
            COLORS['gradient_blue'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD)",
            lambda: self._export_contacts(peer, "txt"))
        action_row.addWidget(exp_txt_btn)

        exp_csv_btn = _action_btn(
            "📊 Export CSV",
            COLORS['gradient_blue'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD)",
            lambda: self._export_contacts(peer, "csv"))
        action_row.addWidget(exp_csv_btn)

        clear_btn = _action_btn(
            "🗑 Clear All",
            COLORS['gradient_red'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149)",
            lambda: self._clear_contacts(peer))
        action_row.addWidget(clear_btn)

        action_row.addStretch()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search contacts…")
        self.search_input.setFixedWidth(220)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 6px 12px;
                color: {COLORS['text_primary']}; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['accent_blue']}; }}
        """)
        self.search_input.textChanged.connect(
            lambda: QTimer.singleShot(300, self._reload_contacts_table))
        action_row.addWidget(self.search_input)
        self.right_layout.addLayout(action_row)

        # ── Contacts table ────────────────────────────────────────────────────
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(5)
        self.contacts_table.setHorizontalHeaderLabels(
            ["Value", "Label", "Status", "Resolved ID", "Actions"])
        hh = self.contacts_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.contacts_table.setColumnWidth(2, 90)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.contacts_table.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.contacts_table.setColumnWidth(4, 80)
        self.contacts_table.verticalHeader().setVisible(False)
        self.contacts_table.setAlternatingRowColors(True)
        self.contacts_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.contacts_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.contacts_table.setFocusPolicy(Qt.FocusPolicy.NoFocus) # FIX: Hide dotted selection box
        self.contacts_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                gridline-color: {COLORS['border_light']};
                outline: 0;
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
                padding: 10px; border: none;
                font-weight: 600; color: {COLORS['text_secondary']};
            }}
        """)
        self.right_layout.addWidget(self.contacts_table)

        self.contacts_info_lbl = QLabel("")
        self.contacts_info_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;")
        self.right_layout.addWidget(self.contacts_info_lbl)

        self._reload_contacts_table()

    def _reload_contacts_table(self):
        if not self.current_peer:
            return
        search = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        try:
            contacts = self.data.get_contacts(
                self.current_peer["id"],
                search=search or None,
                limit=1000)
        except Exception as e:
            toast_error(f"Failed to load contacts: {e}")
            return

        self.contacts_table.setRowCount(len(contacts))
        status_colors = {
            "pending": COLORS['accent_yellow'],
            "sent":    COLORS['accent_green'],
            "failed":  COLORS['accent_red'],
            "invalid": COLORS['text_muted'],
            "duplicate": COLORS['text_muted'],
        }

        for row, c in enumerate(contacts):
            self.contacts_table.setItem(row, 0, QTableWidgetItem(c["value"]))
            self.contacts_table.setItem(row, 1, QTableWidgetItem(c["label"]))

            status_item = QTableWidgetItem(c["status"])
            color = status_colors.get(c["status"], COLORS['text_secondary'])
            status_item.setForeground(QColor(color))
            self.contacts_table.setItem(row, 2, status_item)

            rid = str(c["resolved_id"]) if c["resolved_id"] else "—"
            self.contacts_table.setItem(row, 3, QTableWidgetItem(rid))

            # FIX: Action Delete Button - Using 'X' explicitly for better visibility instead of unicode missing symbol
            aw = QWidget()
            aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(4, 3, 4, 3)
            db_btn = QPushButton("X")
            db_btn.setFixedSize(28, 26)
            db_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            db_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']}; border-radius: 5px;
                    color: {COLORS['accent_red']}; font-weight: bold; font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {COLORS['gradient_red']}; border: none; color: white;
                }}
            """)
            db_btn.clicked.connect(
                lambda _, cid=c["id"]: self._delete_contact(cid))
            al.addWidget(db_btn)
            self.contacts_table.setCellWidget(row, 4, aw)
            self.contacts_table.setRowHeight(row, 38)

        total = len(contacts)
        self.contacts_info_lbl.setText(
            f"Showing {total:,} contact(s)" +
            (f" matching '{search}'" if search else ""))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _create_peer(self):
        dlg = PeerDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                self.data.create_peer(data)
                toast_success(f"Peer '{data['title']}' created")
                self.refresh_peers()
            except Exception as e:
                toast_error(f"Failed: {e}")

    def _edit_peer(self, peer: dict):
        dlg = PeerDialog(peer=peer, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                self.data.update_peer(peer["id"], data)
                toast_success("Peer updated")
                self.refresh_peers()
            except Exception as e:
                toast_error(f"Failed: {e}")

    def _delete_peer(self, peer: dict):
        reply = QMessageBox.question(
            self, "Delete Peer",
            f"Delete peer '{peer['title']}' and all its contacts?\n" # FIX: F-string double quotes bug
            f"This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_peer(peer["id"])
                toast_success("Peer deleted")
                self.current_peer = None
                self.refresh_peers()
                self._show_empty_state()
            except Exception as e:
                toast_error(f"Failed: {e}")

    def _import_contacts(self, peer: dict):
        dlg = ImportContactsDialog(peer, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_peers()
            self._build_peer_detail(peer)

    def _export_contacts(self, peer: dict, fmt: str):
        ext = "csv" if fmt == "csv" else "txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Contacts",
            f"contacts_{peer['title'].replace(' ', '_')}.{ext}",
            f"{'CSV' if fmt == 'csv' else 'Text'} Files (*.{ext})")
        if not path:
            return
        try:
            content = self.data.export_peer_contacts(peer["id"], fmt)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            lines = content.strip().splitlines()
            toast_success(f"Exported {len(lines):,} contacts → {os.path.basename(path)}")
        except Exception as e:
            toast_error(f"Export failed: {e}")

    def _clear_contacts(self, peer: dict):
        reply = QMessageBox.question(
            self, "Clear All Contacts",
            f"Delete ALL contacts from '{peer['title']}'?\n" # FIX: F-string double quotes bug
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self.data.clear_peer_contacts(peer["id"])
                toast_success(f"Cleared {deleted:,} contacts")
                self.refresh_peers()
                self._build_peer_detail(peer)
            except Exception as e:
                toast_error(f"Failed: {e}")

    def _delete_contact(self, contact_id: int):
        try:
            self.data.delete_contact(contact_id)
            self._reload_contacts_table()
        except Exception as e:
            toast_error(f"Failed: {e}")
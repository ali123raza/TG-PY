"""
Templates Page — Upgraded
- Categories / tags
- Multiple text variants (anti-spam random rotation)
- Variable placeholders: {name}, {username}, {phone}, {custom_1}
- Live preview
- Quick send from template
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QScrollArea, QSplitter,
    QListWidget, QListWidgetItem, QTabWidget, QApplication,
    QSpinBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

from data_service import get_data_service
from toast import toast_success, toast_error, toast_info, toast_warning

data_service = get_data_service()

COLORS = {
    'bg_primary':      '#0D1117',
    'bg_secondary':    '#161B22',
    'bg_tertiary':     '#21262D',
    'bg_hover':        '#30363D',
    'text_primary':    '#F0F6FC',
    'text_secondary':  '#8B949E',
    'text_muted':      '#6E7681',
    'text_inverse':    '#0D1117',
    'border':          '#30363D',
    'border_light':    '#21262D',
    'accent_blue':     '#58A6FF',
    'accent_blue_dark':'#1F6FEB',
    'accent_green':    '#3FB950',
    'accent_green_dark':'#238636',
    'accent_red':      '#F85149',
    'accent_yellow':   '#D29922',
    'accent_purple':   '#A371F7',
    'gradient_blue':   'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #58A6FF,stop:1 #1F6FEB)',
    'gradient_green':  'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3FB950,stop:1 #238636)',
    'gradient_red':    'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F85149,stop:1 #DA3633)',
    'gradient_purple': 'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #A371F7,stop:1 #8957E5)',
}

AVAILABLE_VARS = [
    ("{name}",      "Recipient's name"),
    ("{username}",  "Telegram @username"),
    ("{phone}",     "Phone number"),
    ("{custom_1}",  "Custom field 1"),
    ("{custom_2}",  "Custom field 2"),
    ("{custom_3}",  "Custom field 3"),
]


def _btn(label, gradient, hover, cb, w=None, h=30):
    b = QPushButton(label)
    b.setFixedHeight(h)
    if w:
        b.setFixedWidth(w)
    else:
        b.setMinimumWidth(60)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background: {gradient}; border: none;
            border-radius: 6px; color: white;
            font-weight: 600; font-size: 11px; padding: 0 10px;
        }}
        QPushButton:hover {{ background: {hover}; }}
    """)
    b.clicked.connect(cb)
    return b


# ─────────────────────────────────────────────────────────────────────────────
# Template Builder Dialog (create + edit)
# ─────────────────────────────────────────────────────────────────────────────

class TemplateBuilderDialog(QDialog):
    def __init__(self, template: dict = None, parent=None):
        super().__init__(parent)
        self.template = template
        self.setWindowTitle("Edit Template" if template else "New Template")
        self.setMinimumSize(820, 680)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_secondary']}; }}
            QLabel  {{ color: {COLORS['text_primary']}; font-size: 13px; }}
            QLineEdit, QComboBox, QTextEdit, QSpinBox {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 12px;
                color: {COLORS['text_primary']}; font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border-color: {COLORS['accent_blue']};
            }}
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 16px;
                color: {COLORS['text_primary']}; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {COLORS['bg_hover']}; }}
            QTabWidget::pane {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']}; border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                padding: 8px 20px; border-radius: 6px 6px 0 0;
                color: {COLORS['text_secondary']};
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['accent_blue']};
            }}
        """)
        self._variant_editors: list[QTextEdit] = []
        self._build_ui()
        if template:
            self._load(template)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        # ── Name + category row ───────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        name_col = QVBoxLayout()
        name_col.addWidget(QLabel("Template Name *"))
        self.name_input = QLineEdit(
            self.template["name"] if self.template else "")
        self.name_input.setPlaceholderText("e.g. Welcome Message")
        name_col.addWidget(self.name_input)
        top_row.addLayout(name_col, stretch=2)

        cat_col = QVBoxLayout()
        cat_col.addWidget(QLabel("Category"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("— None —", None)
        try:
            for cat in data_service.get_template_categories():
                self.cat_combo.addItem(cat["name"], cat["id"])
        except Exception:
            pass
        cat_col.addWidget(self.cat_combo)
        top_row.addLayout(cat_col, stretch=1)
        layout.addLayout(top_row)

        # ── Main tabs ─────────────────────────────────────────────────────────
        tabs = QTabWidget()

        # ── Tab 1: Text / Variants ────────────────────────────────────────────
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        text_layout.setSpacing(10)

        # Variants toggle
        variant_row = QHBoxLayout()
        self.use_variants_check = QCheckBox(
            "Use multiple variants  "
            "(random pick per send — anti-spam)")
        self.use_variants_check.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 13px;")
        self.use_variants_check.toggled.connect(self._toggle_variants_ui)
        variant_row.addWidget(self.use_variants_check)
        variant_row.addStretch()
        text_layout.addLayout(variant_row)

        # Single text area
        self.single_text_widget = QWidget()
        stl = QVBoxLayout(self.single_text_widget)
        stl.setContentsMargins(0, 0, 0, 0)
        stl.addWidget(QLabel("Message Text"))
        self.main_text = QTextEdit()
        self.main_text.setPlaceholderText(
            "Hello {name}, welcome!\n\n"
            "Available variables: {name} {username} {phone} {custom_1}")
        self.main_text.setMinimumHeight(180)
        stl.addWidget(self.main_text)
        text_layout.addWidget(self.single_text_widget)

        # Variants area (hidden by default)
        self.variants_widget = QWidget()
        vl = QVBoxLayout(self.variants_widget)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)

        variants_header = QHBoxLayout()
        variants_header.addWidget(QLabel("Text Variants  (one per box, random rotation)"))
        variants_header.addStretch()
        add_variant_btn = QPushButton("+ Add Variant")
        add_variant_btn.setFixedHeight(28)
        add_variant_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['accent_blue']};
                border-radius: 6px; color: {COLORS['accent_blue']};
                font-size: 12px; padding: 0 10px;
            }}
            QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        add_variant_btn.clicked.connect(self._add_variant_box)
        variants_header.addWidget(add_variant_btn)
        vl.addLayout(variants_header)

        self.variants_scroll = QScrollArea()
        self.variants_scroll.setWidgetResizable(True)
        self.variants_scroll.setMinimumHeight(280)
        self.variants_inner = QWidget()
        self.variants_inner_layout = QVBoxLayout(self.variants_inner)
        self.variants_inner_layout.setSpacing(8)
        self.variants_inner_layout.addStretch()
        self.variants_scroll.setWidget(self.variants_inner)
        vl.addWidget(self.variants_scroll)
        self.variants_widget.setVisible(False)
        text_layout.addWidget(self.variants_widget)

        # Variables quick-insert
        vars_frame = QFrame()
        vars_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px; padding: 6px;
            }}
        """)
        vars_layout = QHBoxLayout(vars_frame)
        vars_layout.setContentsMargins(10, 6, 10, 6)
        vars_layout.addWidget(QLabel("Insert variable:"))
        for tag, tooltip in AVAILABLE_VARS:
            vb = QPushButton(tag)
            vb.setFixedHeight(26)
            vb.setToolTip(tooltip)
            vb.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 5px; color: {COLORS['accent_blue']};
                    font-size: 12px; padding: 0 8px;
                }}
                QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
            """)
            vb.clicked.connect(lambda _, t=tag: self._insert_variable(t))
            vars_layout.addWidget(vb)
        vars_layout.addStretch()
        text_layout.addWidget(vars_frame)
        text_layout.addStretch()
        tabs.addTab(text_tab, "✉  Message")

        # ── Tab 2: Media ──────────────────────────────────────────────────────
        media_tab = QWidget()
        media_layout = QVBoxLayout(media_tab)
        media_layout.setSpacing(10)
        media_layout.setContentsMargins(12, 12, 12, 12)

        self.media_path_label = QLabel("No media attached")
        self.media_path_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 13px;")
        media_layout.addWidget(self.media_path_label)

        media_btn_row = QHBoxLayout()
        choose_media = QPushButton("📁  Choose File")
        choose_media.clicked.connect(self._choose_media)
        media_btn_row.addWidget(choose_media)
        clear_media = QPushButton("✕  Remove Media")
        clear_media.clicked.connect(self._clear_media)
        media_btn_row.addWidget(clear_media)
        media_btn_row.addStretch()
        media_layout.addLayout(media_btn_row)

        self.media_type_combo = QComboBox()
        self.media_type_combo.addItems(["photo", "video", "audio", "document"])
        media_layout.addWidget(QLabel("Media Type (auto-detected if left as photo):"))
        media_layout.addWidget(self.media_type_combo)
        media_layout.addStretch()
        tabs.addTab(media_tab, "🖼  Media")

        # ── Tab 3: Preview ────────────────────────────────────────────────────
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setSpacing(10)
        preview_layout.setContentsMargins(12, 12, 12, 12)

        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("Sample name:"))
        self.sample_name = QLineEdit("Ahmed Ali")
        self.sample_name.setFixedWidth(160)
        sample_row.addWidget(self.sample_name)
        sample_row.addWidget(QLabel("username:"))
        self.sample_username = QLineEdit("@ahmed_ali")
        self.sample_username.setFixedWidth(140)
        sample_row.addWidget(self.sample_username)
        sample_row.addWidget(QLabel("custom_1:"))
        self.sample_custom1 = QLineEdit("Special Offer")
        self.sample_custom1.setFixedWidth(140)
        sample_row.addWidget(self.sample_custom1)
        refresh_preview_btn = QPushButton("🔄 Refresh")
        refresh_preview_btn.setFixedHeight(28)
        refresh_preview_btn.clicked.connect(self._refresh_preview)
        sample_row.addWidget(refresh_preview_btn)
        sample_row.addStretch()
        preview_layout.addLayout(sample_row)

        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 12px;
                color: {COLORS['text_primary']}; font-size: 14px;
            }}
        """)
        self.preview_box.setPlaceholderText("Preview will appear here…")
        preview_layout.addWidget(self.preview_box)
        tabs.addTab(preview_tab, "👁  Preview")

        layout.addWidget(tabs, stretch=1)

        # ── Bottom buttons ────────────────────────────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_row.addWidget(cancel_btn)
        self.save_btn = _btn(
            "Update Template" if self.template else "Create Template",
            COLORS['gradient_green'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #56D364,stop:1 #2EA043)",
            self._save, w=180, h=36)
        bottom_row.addWidget(self.save_btn)
        layout.addLayout(bottom_row)

        self._media_path = ""
        self._add_variant_box()  # start with one empty variant box (hidden)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _toggle_variants_ui(self, checked: bool):
        self.single_text_widget.setVisible(not checked)
        self.variants_widget.setVisible(checked)

    def _add_variant_box(self, text: str = ""):
        idx = len(self._variant_editors) + 1
        box_widget = QWidget()
        box_layout = QVBoxLayout(box_widget)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(QLabel(f"Variant {idx}"))
        header.addStretch()
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {COLORS['text_muted']}; font-size: 14px;
            }}
            QPushButton:hover {{ color: {COLORS['accent_red']}; }}
        """)

        editor = QTextEdit()
        editor.setPlainText(text)
        editor.setMinimumHeight(80)
        editor.setMaximumHeight(120)
        editor.setPlaceholderText(f"Variant {idx} text…")
        self._variant_editors.append(editor)

        remove_btn.clicked.connect(
            lambda _, w=box_widget, e=editor: self._remove_variant(w, e))
        header.addWidget(remove_btn)
        box_layout.addLayout(header)
        box_layout.addWidget(editor)

        # Insert before the stretch
        count = self.variants_inner_layout.count()
        self.variants_inner_layout.insertWidget(count - 1, box_widget)

    def _remove_variant(self, widget: QWidget, editor: QTextEdit):
        if len(self._variant_editors) <= 1:
            toast_warning("At least one variant required")
            return
        self._variant_editors.remove(editor)
        widget.deleteLater()

    def _insert_variable(self, tag: str):
        if self.use_variants_check.isChecked() and self._variant_editors:
            # Insert into the last focused variant — for simplicity use last
            self._variant_editors[-1].insertPlainText(tag)
        else:
            self.main_text.insertPlainText(tag)

    def _choose_media(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Media File", "",
            "Media Files (*.jpg *.jpeg *.png *.gif *.mp4 *.mov *.mp3 *.ogg *.pdf *.zip *.*);;All Files (*)")
        if path:
            self._media_path = path
            self.media_path_label.setText(f"✓  {os.path.basename(path)}")
            self.media_path_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 13px;")
            # Auto-detect type
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                self.media_type_combo.setCurrentText("photo")
            elif ext in (".mp4", ".mov", ".avi", ".mkv"):
                self.media_type_combo.setCurrentText("video")
            elif ext in (".mp3", ".ogg", ".wav", ".m4a"):
                self.media_type_combo.setCurrentText("audio")
            else:
                self.media_type_combo.setCurrentText("document")

    def _clear_media(self):
        self._media_path = ""
        self.media_path_label.setText("No media attached")
        self.media_path_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 13px;")

    def _refresh_preview(self):
        text = self._get_active_text()
        if not text:
            self.preview_box.setPlainText("(no text)")
            return
        variables = {
            "name":     self.sample_name.text() or "Ahmed Ali",
            "username": self.sample_username.text() or "@username",
            "phone":    "+923001234567",
            "custom_1": self.sample_custom1.text() or "Value",
            "custom_2": "Value2",
            "custom_3": "Value3",
        }
        for k, v in variables.items():
            text = text.replace(f"{{{k}}}", v)
        self.preview_box.setPlainText(text)

    def _get_active_text(self) -> str:
        if self.use_variants_check.isChecked() and self._variant_editors:
            # Show first non-empty variant
            for ed in self._variant_editors:
                t = ed.toPlainText().strip()
                if t:
                    return t
            return ""
        return self.main_text.toPlainText().strip()

    # ── Load existing template ────────────────────────────────────────────────

    def _load(self, t: dict):
        self.name_input.setText(t["name"])

        # Category
        for i in range(self.cat_combo.count()):
            if self.cat_combo.itemData(i) == t.get("category_id"):
                self.cat_combo.setCurrentIndex(i)
                break

        # Variants
        use_v = t.get("use_variants", False)
        self.use_variants_check.setChecked(use_v)
        self._toggle_variants_ui(use_v)

        if use_v and t.get("variants"):
            # Clear default empty box
            for ed in self._variant_editors:
                ed.parentWidget().deleteLater()
            self._variant_editors.clear()
            for v in t["variants"]:
                self._add_variant_box(v["text"])
        else:
            self.main_text.setPlainText(t.get("text", ""))

        # Media
        if t.get("media_path"):
            self._media_path = t["media_path"]
            self.media_path_label.setText(f"✓  {os.path.basename(t['media_path'])}")
            self.media_path_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 13px;")
            mt = t.get("media_type", "photo")
            self.media_type_combo.setCurrentText(mt)

    # ── Save ─────────────────────────────────────────────────────────────────

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            toast_error("Please enter a template name")
            return

        use_variants = self.use_variants_check.isChecked()

        if use_variants:
            variants = [ed.toPlainText().strip()
                        for ed in self._variant_editors
                        if ed.toPlainText().strip()]
            if not variants:
                toast_error("Add at least one variant text")
                return
            main_text = variants[0]   # primary text = first variant
        else:
            main_text = self.main_text.toPlainText().strip()
            variants = []
            if not main_text:
                toast_error("Please enter message text")
                return

        # Detect variables used
        import re
        all_text = main_text + " " + " ".join(variants)
        vars_used = re.findall(r'\{(\w+)\}', all_text)
        vars_used = list(dict.fromkeys(vars_used))   # deduplicate

        # Media — save to media dir if local file
        media_path = ""
        media_type = self.media_type_combo.currentText()
        if self._media_path:
            if os.path.exists(self._media_path):
                try:
                    media_path = data_service.save_media(self._media_path)
                except Exception as e:
                    toast_error(f"Media save failed: {e}")
                    return
            else:
                media_path = self._media_path   # already saved path

        payload = {
            "name":          name,
            "text":          main_text,
            "category_id":   self.cat_combo.currentData(),
            "use_variants":  use_variants,
            "variants":      variants,
            "variables_used": vars_used,
            "media_path":    media_path or None,
            "media_type":    media_type if media_path else None,
        }

        self.save_btn.setEnabled(False)
        self.save_btn.setText("Saving…")
        try:
            if self.template:
                data_service.update_template(self.template["id"], payload)
                toast_success("Template updated!")
            else:
                data_service.create_template(payload)
                toast_success("Template created!")
            self.accept()
        except Exception as e:
            toast_error(f"Failed to save: {e}")
        finally:
            self.save_btn.setEnabled(True)
            self.save_btn.setText(
                "Update Template" if self.template else "Create Template")


# ─────────────────────────────────────────────────────────────────────────────
# Category Manager Dialog
# ─────────────────────────────────────────────────────────────────────────────

class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Categories")
        self.setMinimumSize(380, 400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_secondary']}; }}
            QLabel  {{ color: {COLORS['text_primary']}; }}
            QLineEdit {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px;
                color: {COLORS['text_primary']};
            }}
            QPushButton {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px; padding: 6px 14px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{ background-color: {COLORS['bg_hover']}; }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("📂  Template Categories"))

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px; border-radius: 6px; color: {COLORS['text_primary']};
            }}
            QListWidget::item:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        layout.addWidget(self.list_widget)

        add_row = QHBoxLayout()
        self.new_cat_input = QLineEdit()
        self.new_cat_input.setPlaceholderText("New category name…")
        add_row.addWidget(self.new_cat_input)
        add_btn = _btn(
            "+ Add",
            COLORS['gradient_green'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #56D364,stop:1 #2EA043)",
            self._add_cat, w=80)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        del_row = QHBoxLayout()
        del_row.addStretch()
        del_btn = _btn(
            "Delete Selected",
            COLORS['gradient_red'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149)",
            self._del_cat, w=140)
        del_row.addWidget(del_btn)
        layout.addLayout(del_row)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._refresh()

    def _refresh(self):
        self.list_widget.clear()
        try:
            cats = data_service.get_template_categories()
        except Exception:
            cats = []
        for cat in cats:
            item = QListWidgetItem(f"● {cat['name']}")
            item.setForeground(QColor(cat.get("color", "#3FB950")))
            item.setData(Qt.ItemDataRole.UserRole, cat["id"])
            self.list_widget.addItem(item)

    def _add_cat(self):
        name = self.new_cat_input.text().strip()
        if not name:
            return
        try:
            data_service.create_template_category(name)
            self.new_cat_input.clear()
            self._refresh()
            toast_success(f"Category '{name}' created")
        except Exception as e:
            toast_error(str(e))

    def _del_cat(self):
        item = self.list_widget.currentItem()
        if not item:
            toast_warning("Select a category first")
            return
        cat_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            data_service.delete_template_category(cat_id)
            self._refresh()
            toast_success("Category deleted")
        except Exception as e:
            toast_error(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Templates Page
# ─────────────────────────────────────────────────────────────────────────────

class TemplatesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = data_service
        self.templates: list[dict] = []
        self._init_ui()
        self.fetch_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        icon = QLabel("📝")
        icon.setStyleSheet("font-size: 32px;")
        header.addWidget(icon)
        title = QLabel("Message Templates")
        title.setStyleSheet(
            f"font-size: 32px; font-weight: bold; "
            f"color: {COLORS['text_primary']}; padding-left: 12px;")
        header.addWidget(title)
        header.addStretch()

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
        refresh_btn.clicked.connect(self.fetch_data)
        header.addWidget(refresh_btn)

        manage_cats_btn = QPushButton("📂 Categories")
        manage_cats_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 16px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
        """)
        manage_cats_btn.clicked.connect(self._manage_categories)
        header.addWidget(manage_cats_btn)

        new_btn = _btn(
            "+ New Template",
            COLORS['gradient_blue'],
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD)",
            self._create_template, w=150, h=36)
        header.addWidget(new_btn)
        layout.addLayout(header)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter by category:"))
        self.cat_filter = QComboBox()
        self.cat_filter.setFixedWidth(200)
        self.cat_filter.setStyleSheet(f"""
            QComboBox {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 6px 12px;
                color: {COLORS['text_primary']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['accent_blue_dark']};
            }}
        """)
        self.cat_filter.addItem("All Categories", None)
        self.cat_filter.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.cat_filter)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Category", "Variants", "Variables", "Media", "Actions"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 80)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 150)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 200)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
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
                background-color: rgba(31,111,235,0.2);
                color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_tertiary']};
                padding: 12px; border: none;
                font-weight: 600; color: {COLORS['text_secondary']};
            }}
        """)
        layout.addWidget(self.table)

    # ── Data ──────────────────────────────────────────────────────────────────

    def fetch_data(self):
        try:
            self.templates = self.data.get_templates()
            # Refresh category filter
            current_cat = self.cat_filter.currentData()
            self.cat_filter.blockSignals(True)
            self.cat_filter.clear()
            self.cat_filter.addItem("All Categories", None)
            try:
                for cat in self.data.get_template_categories():
                    self.cat_filter.addItem(cat["name"], cat["id"])
            except Exception:
                pass
            # Restore selection
            for i in range(self.cat_filter.count()):
                if self.cat_filter.itemData(i) == current_cat:
                    self.cat_filter.setCurrentIndex(i)
                    break
            self.cat_filter.blockSignals(False)
            self._apply_filter()
        except Exception as e:
            toast_error(f"Failed to load templates: {e}")

    def _apply_filter(self):
        cat_id = self.cat_filter.currentData()
        if cat_id is None:
            filtered = self.templates
        else:
            filtered = [t for t in self.templates
                        if t.get("category_id") == cat_id]
        self._update_table(filtered)

    def _update_table(self, templates: list):
        self.table.setRowCount(len(templates))
        for row, t in enumerate(templates):
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(t["name"]))

            # Category
            cat = t.get("category")
            if cat:
                cat_item = QTableWidgetItem(f"● {cat['name']}")
                cat_item.setForeground(
                    QColor(cat.get("color", COLORS['accent_green'])))
            else:
                cat_item = QTableWidgetItem("—")
                cat_item.setForeground(QColor(COLORS['text_muted']))
            self.table.setItem(row, 1, cat_item)

            # Variants
            vc = t.get("variant_count", 0)
            v_item = QTableWidgetItem(
                f"🔀 {vc} variants" if t.get("use_variants") and vc
                else "Single")
            v_item.setForeground(
                QColor(COLORS['accent_purple'] if t.get("use_variants")
                       else COLORS['text_muted']))
            self.table.setItem(row, 2, v_item)

            # Variables
            vars_list = t.get("variables_used", [])
            vars_str = ", ".join(f"{{{v}}}" for v in vars_list) if vars_list else "—"
            vars_item = QTableWidgetItem(vars_str)
            vars_item.setForeground(QColor(COLORS['accent_blue']
                                           if vars_list else COLORS['text_muted']))
            self.table.setItem(row, 3, vars_item)

            # Media
            media_item = QTableWidgetItem(
                f"✓ {t['media_type']}" if t.get("media_path") else "—")
            media_item.setForeground(
                QColor(COLORS['accent_green']
                       if t.get("media_path") else COLORS['text_muted']))
            self.table.setItem(row, 4, media_item)

            # Actions
            aw = QWidget()
            aw.setStyleSheet("background: transparent;")
            al = QHBoxLayout(aw)
            al.setContentsMargins(4, 3, 4, 3)
            al.setSpacing(5)

            preview_btn = QPushButton("👁")
            preview_btn.setFixedSize(30, 28)
            preview_btn.setToolTip("Preview")
            preview_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 5px; color: {COLORS['text_primary']};
                    font-size: 13px;
                }}
                QPushButton:hover {{ background: {COLORS['bg_hover']}; }}
            """)
            preview_btn.clicked.connect(
                lambda _, tmpl=t: self._preview_template(tmpl))
            al.addWidget(preview_btn)

            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(30, 28)
            edit_btn.setToolTip("Edit")
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #58A6FF,stop:1 #1F6FEB);
                    border: none; border-radius: 5px;
                    color: white; font-size: 13px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #79B8FF,stop:1 #388BFD);
                }}
            """)
            edit_btn.clicked.connect(
                lambda _, tmpl=t: self._edit_template(tmpl))
            al.addWidget(edit_btn)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(30, 28)
            del_btn.setToolTip("Delete")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F85149,stop:1 #DA3633);
                    border: none; border-radius: 5px;
                    color: white; font-size: 13px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF7B72,stop:1 #F85149);
                }}
            """)
            del_btn.clicked.connect(
                lambda _, tmpl=t: self._delete_template(tmpl))
            al.addWidget(del_btn)
            al.addStretch()

            self.table.setCellWidget(row, 5, aw)
            self.table.setRowHeight(row, 44)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _create_template(self):
        dlg = TemplateBuilderDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.fetch_data()

    def _edit_template(self, template: dict):
        dlg = TemplateBuilderDialog(template=template, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.fetch_data()

    def _preview_template(self, template: dict):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Preview — {template['name']}")
        dlg.setMinimumSize(440, 320)
        dlg.setStyleSheet(f"QDialog {{ background: {COLORS['bg_secondary']}; }}")
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)

        info = QLabel(
            f"<b>{template['name']}</b>"
            + (f"  <span style='color:{COLORS['text_muted']}'>({template['variant_count']} variants)</span>"
               if template.get("use_variants") else ""))
        info.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px;")
        layout.addWidget(info)

        preview_box = QTextEdit()
        preview_box.setReadOnly(True)
        preview_box.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 12px;
                color: {COLORS['text_primary']}; font-size: 14px;
            }}
        """)
        try:
            text = self.data.preview_template(template["id"])
            preview_box.setPlainText(text or "(empty)")
        except Exception:
            preview_box.setPlainText(template.get("text", "(empty)"))
        layout.addWidget(preview_box)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def _delete_template(self, template: dict):
        reply = QMessageBox.question(
            self, "Delete Template",
            f"Delete template '{template['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data.delete_template(template["id"])
                toast_success("Template deleted")
                self.fetch_data()
            except Exception as e:
                toast_error(f"Failed: {e}")

    def _manage_categories(self):
        dlg = CategoryManagerDialog(parent=self)
        dlg.exec()
        self.fetch_data()   # refresh category filter

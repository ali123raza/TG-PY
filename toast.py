"""Toast notification component for PyQt6"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve,
    pyqtSignal, QObject, QEvent,
)
from PyQt6.QtGui import QColor

TOAST_WIDTH = 320
TOAST_HEIGHT = 60  # Fallback height before layout settles
TOAST_SPACING = 10
MARGIN_RIGHT = 20
MARGIN_BOTTOM = 20


class Toast(QWidget):
    """Individual toast notification widget (child of parent window)."""

    closed = pyqtSignal()

    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        parent: QWidget = None,
        duration: int = 4000,
    ):
        super().__init__(parent)
        self.message = message
        self.toast_type = toast_type
        self.duration = duration

        # Keep explicit references so animations are not garbage-collected.
        self._slide_in_anim: QPropertyAnimation | None = None
        self._slide_out_anim: QPropertyAnimation | None = None
        self._reposition_anim: QPropertyAnimation | None = None

        self._setup_ui()
        self._apply_styles()

        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)          # FIX: was not single-shot
        self._close_timer.timeout.connect(self.hide_toast)
        self._close_timer.start(duration)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        # FIX: No window flags — this is a plain child widget.
        # FramelessWindowHint on a child is harmless but WindowStaysOnTopHint
        # would promote it to a top-level OS window, breaking parent layout.
        self.setFixedWidth(TOAST_WIDTH)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        icon = QLabel(self._get_icon())
        icon.setFixedWidth(22)
        icon.setStyleSheet("font-size: 18px; background: transparent;")
        layout.addWidget(icon)

        msg = QLabel(self.message)
        msg.setWordWrap(True)
        msg.setStyleSheet("background: transparent; font-size: 13px; color: white;")
        layout.addWidget(msg, stretch=1)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide_toast)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 18px;
                font-weight: bold;
                color: rgba(255,255,255,0.7);
            }
            QPushButton:hover {
                color: white;
                background: rgba(255,255,255,0.1);
                border-radius: 12px;
            }
        """)
        layout.addWidget(close_btn)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        # FIX: resolve actual size before caller reads width()/height()
        self.adjustSize()

    def _get_icon(self) -> str:
        return {"success": "✓", "error": "✕", "warning": "⚠", "info": "ℹ"}.get(
            self.toast_type, "ℹ"
        )

    def _get_colors(self) -> tuple[str, str]:
        palette = {
            "success": ("#065f46", "#10b981"),
            "error":   ("#7f1d1d", "#ef4444"),
            "warning": ("#713f12", "#f59e0b"),
            "info":    ("#1e3a8a", "#3b82f6"),
        }
        return palette.get(self.toast_type, palette["info"])

    def _apply_styles(self):
        bg, border = self._get_colors()
        self.setStyleSheet(f"""
            Toast {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel {{
                color: white;
                background: transparent;
            }}
        """)

    # ------------------------------------------------------------------
    # Animation helpers
    # ------------------------------------------------------------------

    def show_at(self, x: int, y: int):
        """Place the toast and play slide-in from the right."""
        # FIX: positions are parent-relative; no screen-coord clamping needed.
        # Start just off the right edge of the parent.
        off_x = x + self.width() + MARGIN_RIGHT
        self.move(off_x, y)
        self.show()
        self.raise_()

        # FIX: store animation on self to prevent GC mid-run.
        self._slide_in_anim = QPropertyAnimation(self, b"pos")
        self._slide_in_anim.setDuration(300)
        self._slide_in_anim.setStartValue(QPoint(off_x, y))
        self._slide_in_anim.setEndValue(QPoint(x, y))
        self._slide_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_in_anim.start()

    def move_to(self, x: int, y: int):
        """Animate repositioning (used when other toasts close)."""
        # FIX: keep anim reference so it isn't GC'd.
        self._reposition_anim = QPropertyAnimation(self, b"pos")
        self._reposition_anim.setDuration(200)
        self._reposition_anim.setStartValue(self.pos())
        self._reposition_anim.setEndValue(QPoint(x, y))
        self._reposition_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._reposition_anim.start()

    def hide_toast(self):
        """Slide out, then destroy."""
        self._close_timer.stop()

        # Stop any in-progress slide-in before reversing.
        if self._slide_in_anim and self._slide_in_anim.state() == QPropertyAnimation.State.Running:
            self._slide_in_anim.stop()

        end_x = self.pos().x() + self.width() + MARGIN_RIGHT

        self._slide_out_anim = QPropertyAnimation(self, b"pos")
        self._slide_out_anim.setDuration(250)
        self._slide_out_anim.setStartValue(self.pos())
        self._slide_out_anim.setEndValue(QPoint(end_x, self.pos().y()))
        self._slide_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._slide_out_anim.finished.connect(self._on_hidden)
        self._slide_out_anim.start()

    def _on_hidden(self):
        self.hide()
        self.closed.emit()   # notify manager before deletion
        self.deleteLater()


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ToastManager(QObject):
    """
    Manages a stack of Toast child-widgets anchored to a parent QWidget.

    FIX: Changed from QWidget overlay to QObject + event-filter so that:
      - no transparent-for-mouse-events flag is needed,
      - no spurious top-level window is created,
      - toasts receive mouse events normally.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._parent_widget = parent
        self._toasts: list[Toast] = []
        self._max_toasts = 5

        # FIX: install event-filter instead of relying on resizeEvent of a
        # QWidget overlay (which had its own geometry issues).
        parent.installEventFilter(self)

    # ------------------------------------------------------------------
    # Qt event filter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        if obj is self._parent_widget and event.type() == QEvent.Type.Resize:
            self._reposition_all()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_toast(self, message: str, toast_type: str = "info", duration: int = 4000):
        # Evict oldest if at capacity.
        if len(self._toasts) >= self._max_toasts:
            evicted = self._toasts.pop(0)
            evicted.closed.disconnect()   # avoid double-remove
            evicted.hide_toast()

        toast = Toast(message, toast_type, self._parent_widget, duration)
        toast.closed.connect(lambda t=toast: self._on_toast_closed(t))
        self._toasts.append(toast)

        # Show new toast at its target slot (bottom of stack).
        x, y = self._slot_position(len(self._toasts) - 1)
        toast.show_at(x, y)

        # Push older toasts upward.
        self._reposition_all(skip_index=len(self._toasts) - 1)

    def success(self, message: str): self.show_toast(message, "success")
    def error(self, message: str):   self.show_toast(message, "error")
    def warning(self, message: str): self.show_toast(message, "warning")
    def info(self, message: str):    self.show_toast(message, "info")

    def clear_all(self):
        for t in list(self._toasts):
            t.closed.disconnect()
            t.hide_toast()
        self._toasts.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _slot_position(self, index: int) -> tuple[int, int]:
        """
        Return (x, y) in parent coordinates for the toast at list *index*.

        Convention: newest toast (last in list) sits at the bottom;
        older ones stack upward.
          slot 0  → bottom (newest)
          slot n  → top    (oldest)
        """
        pw = self._parent_widget
        count = len(self._toasts)
        slot = count - 1 - index          # 0 = bottom-most

        toast = self._toasts[index]
        h = toast.height() if toast.height() > 0 else TOAST_HEIGHT
        w = toast.width()  if toast.width()  > 0 else TOAST_WIDTH

        x = pw.width()  - MARGIN_RIGHT  - w
        y = pw.height() - MARGIN_BOTTOM - (slot + 1) * h - slot * TOAST_SPACING

        # Keep inside parent bounds.
        x = max(0, x)
        y = max(0, y)
        return x, y

    def _reposition_all(self, skip_index: int = -1):
        """Smoothly move every visible toast to its current slot."""
        for i, toast in enumerate(self._toasts):
            if i == skip_index:
                continue
            x, y = self._slot_position(i)
            toast.move_to(x, y)

    def _on_toast_closed(self, toast: Toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._reposition_all()


# ---------------------------------------------------------------------------
# Module-level convenience API
# ---------------------------------------------------------------------------

_manager: ToastManager | None = None


def init_toast_manager(parent: QWidget) -> ToastManager:
    global _manager
    _manager = ToastManager(parent)
    return _manager


def get_toast_manager() -> ToastManager | None:
    return _manager


def toast_success(message: str):
    if _manager: _manager.success(message)

def toast_error(message: str):
    if _manager: _manager.error(message)

def toast_warning(message: str):
    if _manager: _manager.warning(message)

def toast_info(message: str):
    if _manager: _manager.info(message)

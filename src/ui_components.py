"""
ui_components.py - Reusable UI Panels & Widgets
=================================================
Contains the side panel widgets: move history, evaluation bar, bot
settings, and the coaching feedback panel.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QTextEdit, QScrollArea, QFrame, QSizePolicy,
    QGroupBox, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPalette, QFont, QIcon


# --------------------------------------------------------------------------
# Colour palette
# --------------------------------------------------------------------------
PALETTE = {
    "bg_dark":      "#1a1a2e",
    "bg_card":      "#16213e",
    "bg_surface":   "#0f3460",
    "accent_blue":  "#4cc9f0",
    "accent_gold":  "#f4a261",
    "blunder_red":  "#e63946",
    "mistake_orange": "#f77f00",
    "inaccuracy_yellow": "#f4d03f",
    "best_green":   "#2ecc71",
    "text_primary": "#e0e0e0",
    "text_secondary": "#9ca3af",
}

STYLE_CARD = f"""
    QGroupBox {{
        background-color: {PALETTE['bg_card']};
        border: 1px solid {PALETTE['bg_surface']};
        border-radius: 8px;
        color: {PALETTE['text_primary']};
        font-weight: bold;
        padding-top: 16px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        color: {PALETTE['accent_blue']};
    }}
"""

MOVE_CLASSIFICATION_COLORS = {
    "Best": PALETTE["best_green"],
    "Good": PALETTE["best_green"],
    "Inaccuracy": PALETTE["inaccuracy_yellow"],
    "Mistake": PALETTE["mistake_orange"],
    "Blunder": PALETTE["blunder_red"],
}


# --------------------------------------------------------------------------
# Evaluation Bar Widget
# --------------------------------------------------------------------------

class EvaluationBar(QWidget):
    """Vertical bar showing engine evaluation (White vs Black advantage)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(28)
        self._eval_cp = 0   # centipawns (white POV)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)

        self.black_bar = QLabel()
        self.white_bar = QLabel()

        for bar, color in [(self.black_bar, "#2d2d2d"), (self.white_bar, "#f0f0f0")]:
            bar.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            layout.addWidget(bar)

        self._set_split(0.5)

    def set_eval(self, cp: float) -> None:
        """Update the bar with a centipawn evaluation (clamped to ±500)."""
        self._eval_cp = cp
        clamped = max(-500, min(500, cp))
        # white_fraction = 0.5 + (clamped / 1000)
        white_fraction = 0.5 + (clamped / 1000)
        self._set_split(white_fraction)

    def _set_split(self, white_fraction: float) -> None:
        total = self.height() or 400
        white_h = int(total * white_fraction)
        black_h = total - white_h
        self.black_bar.setFixedHeight(black_h)
        self.white_bar.setFixedHeight(white_h)


# --------------------------------------------------------------------------
# Move History Widget
# --------------------------------------------------------------------------

class MoveHistoryWidget(QGroupBox):
    """Scrollable list of moves played in the game."""

    def __init__(self, parent=None):
        super().__init__("Move History", parent)
        self.setStyleSheet(STYLE_CARD)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none; background: transparent;")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._inner = QVBoxLayout(self._container)
        self._inner.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._inner.setSpacing(2)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

    def add_move(self, move_num: int, white_san: str, black_san: str = "") -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row.setStyleSheet(f"background: {'#1e2a45' if move_num % 2 == 0 else 'transparent'}; border-radius: 4px;")

        num_label = QLabel(f"{move_num}.")
        num_label.setFixedWidth(28)
        num_label.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")

        white_label = QLabel(white_san)
        white_label.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 12px; font-weight: bold;")

        black_label = QLabel(black_san)
        black_label.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 12px;")

        for w in [num_label, white_label, black_label]:
            row_layout.addWidget(w)
        row_layout.addStretch()

        self._inner.addWidget(row)
        # Auto-scroll to bottom
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

    def clear_moves(self) -> None:
        while self._inner.count():
            item = self._inner.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# --------------------------------------------------------------------------
# Bot Settings Widget
# --------------------------------------------------------------------------

class BotSettingsWidget(QGroupBox):
    """Skill level slider and difficulty configuration."""

    def __init__(self, parent=None):
        super().__init__("Bot Settings", parent)
        self.setStyleSheet(STYLE_CARD)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        self._label = QLabel("Skill Level: 5")
        self._label.setStyleSheet(f"color: {PALETTE['accent_gold']}; font-size: 13px;")
        layout.addWidget(self._label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 20)
        self.slider.setValue(5)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {PALETTE['bg_surface']}; height: 6px; border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {PALETTE['accent_blue']}; width: 16px; height: 16px;
                border-radius: 8px; margin: -5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {PALETTE['accent_blue']}; border-radius: 3px;
            }}
        """)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

        self._difficulty_labels = QLabel("← Beginner      Master →")
        self._difficulty_labels.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 10px;")
        layout.addWidget(self._difficulty_labels)

    def _on_value_changed(self, value: int) -> None:
        labels = {
            range(1, 4): "Beginner", range(4, 8): "Intermediate",
            range(8, 13): "Advanced", range(13, 18): "Expert",
            range(18, 21): "Master",
        }
        label = next((v for k, v in labels.items() if value in k), "")
        self._label.setText(f"Skill Level: {value}  [{label}]")

    @property
    def skill_level(self) -> int:
        return self.slider.value()


# --------------------------------------------------------------------------
# Coaching Panel Widget
# --------------------------------------------------------------------------

class CoachingPanel(QGroupBox):
    """Displays LLM-generated coaching feedback after the game."""

    def __init__(self, parent=None):
        super().__init__("🧠 AI Coach Feedback", parent)
        self.setStyleSheet(STYLE_CARD + f"""
            QTextEdit {{
                background-color: {PALETTE['bg_dark']};
                color: {PALETTE['text_primary']};
                border: none; border-radius: 6px;
                font-size: 13px; line-height: 1.5;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(6)

        self._status = QLabel("Complete a game to receive coaching feedback.")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-style: italic;")
        layout.addWidget(self._status)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setMinimumHeight(150)
        layout.addWidget(self._text)

        self._stats_row = QHBoxLayout()
        self._stat_labels: dict[str, QLabel] = {}
        for key in ["Blunders", "Mistakes", "Inaccuracies", "Accuracy"]:
            frame = QFrame()
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(6, 4, 6, 4)
            frame.setStyleSheet(f"background: {PALETTE['bg_surface']}; border-radius: 6px;")
            title = QLabel(key)
            title.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 10px; font-weight: bold;")
            val = QLabel("-")
            val.setStyleSheet(f"color: {PALETTE['accent_gold']}; font-size: 15px; font-weight: bold;")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(title)
            frame_layout.addWidget(val)
            self._stat_labels[key] = val
            self._stats_row.addWidget(frame)

        layout.addLayout(self._stats_row)

    def update_stats(self, blunders: int, mistakes: int, inaccuracies: int, accuracy: str) -> None:
        self._stat_labels["Blunders"].setText(str(blunders))
        self._stat_labels["Blunders"].setStyleSheet(f"color: {PALETTE['blunder_red']}; font-size:15px; font-weight:bold;")
        self._stat_labels["Mistakes"].setText(str(mistakes))
        self._stat_labels["Mistakes"].setStyleSheet(f"color: {PALETTE['mistake_orange']}; font-size:15px; font-weight:bold;")
        self._stat_labels["Inaccuracies"].setText(str(inaccuracies))
        self._stat_labels["Inaccuracies"].setStyleSheet(f"color: {PALETTE['inaccuracy_yellow']}; font-size:15px; font-weight:bold;")
        self._stat_labels["Accuracy"].setText(accuracy)
        self._stat_labels["Accuracy"].setStyleSheet(f"color: {PALETTE['best_green']}; font-size:15px; font-weight:bold;")

    def set_feedback(self, text: str) -> None:
        self._status.setText("Post-game analysis complete:")
        self._text.setPlainText(text)

    def set_loading(self, loading: bool) -> None:
        if loading:
            self._status.setText("⏳ Analysing game with AI coach...")
            self._text.setPlainText("")
        else:
            self._status.setText("Post-game analysis complete:")

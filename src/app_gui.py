"""
app_gui.py - Main PyQt6 Application & Chess Board Renderer
============================================================
Renders the chess board, handles mouse input (click-to-move),
orchestrates game flow between the human player and bot, and triggers
post-game analysis with AI coaching.
"""

import os
import sys
import threading
import chess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QSplitter, QStatusBar
)
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QObject, QThread
from PyQt6.QtGui import (
    QPainter, QColor, QPixmap, QPen, QBrush, QFont, QFontDatabase
)

from .engine_manager import EngineManager
from .game_loop import GameLoop
from .analyzer import Analyzer
from .coach_llm import ChessCoach
from .ui_components import (
    EvaluationBar, MoveHistoryWidget, BotSettingsWidget,
    CoachingPanel, PALETTE
)

# --------------------------------------------------------------------------
# Colours for the board — clean black & white minimalistic
# --------------------------------------------------------------------------
LIGHT_SQUARE = QColor("#f5f5f5")   # near-white
DARK_SQUARE  = QColor("#202020")   # near-black
HIGHLIGHT_SRC   = QColor(80, 180, 240, 160)   # blue tint for selected piece
HIGHLIGHT_LEGAL = QColor(80, 180, 240, 70)    # blue tint for legal dots
LAST_MOVE   = QColor(100, 220, 100, 100)       # green tint for last move
CHECK_COLOR = QColor(220, 50, 50, 200)         # red for king in check

# Unicode chess pieces (fallback if no image assets)
UNICODE_PIECES = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}


# --------------------------------------------------------------------------
# Worker thread for post-game analysis (keeps UI responsive)
# --------------------------------------------------------------------------

class AnalysisWorker(QObject):
    finished = pyqtSignal(object, object, str)   # report, critical_moments, summary
    error = pyqtSignal(str)

    def __init__(self, engine: EngineManager, game_loop: GameLoop, coach: ChessCoach):
        super().__init__()
        self.engine = engine
        self.game_loop = game_loop
        self.coach = coach

    def run(self):
        try:
            analyzer = Analyzer(self.engine)
            player_color = "white" if self.game_loop.player_color == chess.WHITE else "black"
            report = analyzer.analyse_game(self.game_loop.move_history, player_color=player_color)
            critical = self.coach.explain_critical_moments(report)
            summary = self.coach.generate_game_summary(report, self.game_loop.get_outcome_description())
            self.finished.emit(report, critical, summary)
        except Exception as e:
            self.error.emit(str(e))


# --------------------------------------------------------------------------
# Chess Board Widget
# --------------------------------------------------------------------------

class ChessBoardWidget(QWidget):
    """Interactive chess board that renders pieces and handles user clicks."""

    move_made = pyqtSignal(str)   # emits UCI move string

    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self._selected_square: chess.Square | None = None
        self._legal_targets: list[chess.Square] = []
        self._last_move: chess.Move | None = None
        self._flipped = False
        self.setMinimumSize(480, 480)

    def set_board(self, board: chess.Board) -> None:
        self.board = board.copy()
        self.update()

    def _sq_from_pixel(self, x: int, y: int) -> chess.Square:
        sq_size = self.width() // 8
        col = x // sq_size
        row = 7 - (y // sq_size)
        if self._flipped:
            col, row = 7 - col, 7 - row
        return chess.square(col, row)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        sq_size = self.width() // 8

        for rank in range(8):
            for file in range(8):
                sq = chess.square(file, rank)
                col = file if not self._flipped else 7 - file
                row = 7 - rank if not self._flipped else rank

                rect = QRect(col * sq_size, row * sq_size, sq_size, sq_size)
                is_light = (file + rank) % 2 == 0
                base_color = LIGHT_SQUARE if is_light else DARK_SQUARE
                painter.fillRect(rect, base_color)

                # Last move highlight
                if self._last_move and sq in (self._last_move.from_square, self._last_move.to_square):
                    painter.fillRect(rect, LAST_MOVE)

                # Selected piece highlight
                if self._selected_square == sq:
                    painter.fillRect(rect, HIGHLIGHT_SRC)

                # Legal move dots
                if sq in self._legal_targets:
                    painter.fillRect(rect, HIGHLIGHT_LEGAL)
                    dot_r = sq_size // 6
                    cx, cy = rect.center().x(), rect.center().y()
                    painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)
                    painter.setBrush(Qt.BrushStyle.NoBrush)

                # King in check
                piece = self.board.piece_at(sq)
                if piece and piece.piece_type == chess.KING and self.board.is_check():
                    if piece.color == self.board.turn:
                        painter.fillRect(rect, CHECK_COLOR)

                # Draw piece
                if piece:
                    sym = UNICODE_PIECES.get(piece.symbol(), "?")
                    font = QFont("Segoe UI Symbol", sq_size // 2)
                    painter.setFont(font)
                    # White pieces: black text on light squares, white text on dark squares
                    if piece.color == chess.WHITE:
                        color = QColor("#f5f5f5") if (file + rank) % 2 == 1 else QColor("#1a1a1a")
                    else:
                        color = QColor("#1a1a1a") if (file + rank) % 2 == 1 else QColor("#f5f5f5")
                    # Add subtle drop shadow for readability
                    painter.setPen(QColor(0, 0, 0, 60))
                    shadow_rect = QRect(rect.x() + 2, rect.y() + 2, rect.width(), rect.height())
                    painter.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, sym)
                    painter.setPen(color)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, sym)

        # Draw rank/file labels
        label_font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(label_font)
        files = "abcdefgh"
        ranks = "12345678"
        for i in range(8):
            f_idx = i if not self._flipped else 7 - i
            # File label colour contrasts with the square in the bottom row
            label_col = QColor("#888") if (i + 0) % 2 == 0 else QColor("#888")
            painter.setPen(QColor("#888888"))
            painter.drawText(
                QRect(i * sq_size, 7 * sq_size + sq_size - 14, sq_size, 14),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                files[f_idx]
            )
            r_idx = 7 - i if not self._flipped else i
            painter.drawText(
                QRect(2, i * sq_size + 2, 16, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                ranks[r_idx]
            )

        painter.end()

    def mousePressEvent(self, event) -> None:
        from PyQt6.QtCore import Qt as QtCore
        if event.button() != QtCore.MouseButton.LeftButton:
            return

        sq = self._sq_from_pixel(event.pos().x(), event.pos().y())

        if self._selected_square is None:
            # First click: select a piece
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                self._selected_square = sq
                self._legal_targets = [
                    m.to_square for m in self.board.legal_moves
                    if m.from_square == sq
                ]
        else:
            # Second click: attempt move
            if sq in self._legal_targets:
                move = chess.Move(self._selected_square, sq)
                # Handle promotions (auto-promote to queen)
                if (self.board.piece_type_at(self._selected_square) == chess.PAWN
                        and chess.square_rank(sq) in (0, 7)):
                    move = chess.Move(self._selected_square, sq, promotion=chess.QUEEN)

                self._last_move = move
                self.move_made.emit(move.uci())
            # Deselect
            self._selected_square = None
            self._legal_targets = []

        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self._flipped = flipped
        self.update()


# --------------------------------------------------------------------------
# Main Application Window
# --------------------------------------------------------------------------

class ChessCoachApp(QMainWindow):
    """Main application window."""

    # Signal for safe cross-thread eval bar updates
    eval_updated = pyqtSignal(float)
    def __init__(self, engine: EngineManager, coach: ChessCoach):
        super().__init__()
        self.engine = engine
        self.coach = coach
        self.game_loop = GameLoop(engine, player_color=chess.WHITE)
        self._analysis_thread: QThread | None = None
        self._pending_eval: float | None = None

        self.setWindowTitle("♟️ ChessC+ — AI Chess Coach")
        self.setMinimumSize(960, 640)
        self._init_ui()
        self.eval_updated.connect(self._apply_eval)   # wire signal → slot (thread-safe)
        self._apply_global_style()
        self._start_new_game()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # Left: board + eval bar
        board_container = QWidget()
        board_row = QHBoxLayout(board_container)
        board_row.setContentsMargins(0, 0, 0, 0)
        board_row.setSpacing(6)

        self.eval_bar = EvaluationBar()
        self.board_widget = ChessBoardWidget()
        self.board_widget.move_made.connect(self._on_player_move)
        board_row.addWidget(self.eval_bar)
        board_row.addWidget(self.board_widget, stretch=1)

        root_layout.addWidget(board_container, stretch=3)

        # Right: side panel
        side_panel = QVBoxLayout()
        side_panel.setSpacing(10)

        # Bot settings
        self.bot_settings = BotSettingsWidget()
        self.bot_settings.slider.valueChanged.connect(self._on_skill_changed)
        side_panel.addWidget(self.bot_settings)

        # New game button
        self.new_game_btn = QPushButton("🆕 New Game")
        self.new_game_btn.setFixedHeight(40)
        self.new_game_btn.clicked.connect(self._start_new_game)
        self.new_game_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PALETTE['accent_blue']};
                color: #1a1a2e; font-size: 14px; font-weight: bold;
                border: none; border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: #38b2e8; }}
        """)
        side_panel.addWidget(self.new_game_btn)

        # Flip board
        flip_btn = QPushButton("🔄 Flip Board")
        flip_btn.setFixedHeight(35)
        flip_btn.clicked.connect(lambda: self.board_widget.set_flipped(not self.board_widget._flipped))
        flip_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PALETTE['bg_surface']};
                color: {PALETTE['text_primary']}; font-size: 13px;
                border: none; border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: #1a4a7a; }}
        """)
        side_panel.addWidget(flip_btn)

        # Move history
        self.move_history = MoveHistoryWidget()
        side_panel.addWidget(self.move_history, stretch=1)

        # Coaching panel
        self.coaching_panel = CoachingPanel()
        side_panel.addWidget(self.coaching_panel, stretch=2)

        side_widget = QWidget()
        side_widget.setLayout(side_panel)
        root_layout.addWidget(side_widget, stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. White to move.")

    def _apply_global_style(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {PALETTE['bg_dark']};
                color: {PALETTE['text_primary']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QStatusBar {{
                background-color: {PALETTE['bg_card']};
                color: {PALETTE['text_secondary']};
                font-size: 12px;
            }}
        """)

    # ------------------------------------------------------------------
    # Game Flow
    # ------------------------------------------------------------------

    def _start_new_game(self) -> None:
        self.game_loop.new_game()
        self.board_widget.set_board(self.engine.board)
        self.move_history.clear_moves()
        self.coaching_panel.set_feedback("")
        self.eval_bar.set_eval(0)
        self.status_bar.showMessage("New game started. White to move.")
        self._move_count_white = 0
        self._move_count_black = 0
        self._current_white_move = ""

    def _on_player_move(self, uci_move: str) -> None:
        if self.game_loop.is_over or not self.game_loop.is_player_turn:
            return

        success = self.game_loop.apply_player_move(uci_move)
        if not success:
            return

        # Record for display
        last = self.game_loop.move_history[-1]
        self._current_white_move = last.san

        self.board_widget.set_board(self.engine.board)
        self._update_eval()

        if self.game_loop.is_over:
            self._on_game_over()
            return

        self.status_bar.showMessage("Bot is thinking...")
        QApplication.processEvents()

        # Bot move — 50ms delay so the board paint event completes first
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._do_bot_move)

    def _do_bot_move(self) -> None:
        san = self.game_loop.apply_bot_move()
        if san:
            # Update move history display
            self._move_count_white += 1
            self.move_history.add_move(self._move_count_white, self._current_white_move, san)

        self.board_widget.set_board(self.engine.board)
        self._update_eval()

        if self.game_loop.is_over:
            self._on_game_over()
        else:
            self.status_bar.showMessage("Your turn. You play as White.")

    def _on_game_over(self) -> None:
        outcome = self.game_loop.get_outcome_description()
        self.status_bar.showMessage(f"Game Over: {outcome}")
        QMessageBox.information(self, "Game Over", f"Result: {outcome}")
        self._run_post_game_analysis()

    def _update_eval(self) -> None:
        """Kick off a background thread for eval — never blocks the UI."""
        import threading
        def _do_eval():
            try:
                cp = self.engine.evaluate_position()  # fast ~50ms
                self.eval_updated.emit(cp)            # safe cross-thread signal
            except Exception:
                pass
        threading.Thread(target=_do_eval, daemon=True).start()

    def _apply_eval(self, cp: float) -> None:
        """Called on the main thread via eval_updated signal."""
        self.eval_bar.set_eval(cp)
        cp_str = f"+{cp:.0f}" if cp > 0 else f"{cp:.0f}"
        self.status_bar.showMessage(f"Evaluation: {cp_str} cp  |  Your turn — you play White")

    # ------------------------------------------------------------------
    # Post-Game Analysis
    # ------------------------------------------------------------------

    def _run_post_game_analysis(self) -> None:
        if not self.game_loop.move_history:
            return

        self.coaching_panel.set_loading(True)

        self._analysis_thread = QThread()
        self._worker = AnalysisWorker(self.engine, self.game_loop, self.coach)
        self._worker.moveToThread(self._analysis_thread)
        self._analysis_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.finished.connect(self._analysis_thread.quit)
        self._analysis_thread.start()

    def _on_analysis_done(self, report, critical_moments, summary) -> None:
        stats = report.summary_stats()
        self.coaching_panel.update_stats(
            blunders=stats["blunders"],
            mistakes=stats["mistakes"],
            inaccuracies=stats["inaccuracies"],
            accuracy=stats["accuracy"],
        )
        self.coaching_panel.set_loading(False)
        self.coaching_panel.set_feedback(summary)
        self.status_bar.showMessage("Analysis complete. Review your coaching feedback →")

    def _on_analysis_error(self, error_msg: str) -> None:
        self.coaching_panel.set_loading(False)
        self.coaching_panel.set_feedback(f"Analysis error: {error_msg}")

    # ------------------------------------------------------------------
    # Bot Settings
    # ------------------------------------------------------------------

    def _on_skill_changed(self, level: int) -> None:
        self.engine.set_skill_level(level)


# --------------------------------------------------------------------------
# Entry point helper
# --------------------------------------------------------------------------

def launch_app(engine: EngineManager, coach: ChessCoach) -> None:
    """Launch the PyQt6 application. Call after engine.start()."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = ChessCoachApp(engine, coach)
    window.show()
    sys.exit(app.exec())

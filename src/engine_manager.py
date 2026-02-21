"""
engine_manager.py - Stockfish Engine Integration & Bot Logic
============================================================
Manages the communication with the Stockfish chess engine for:
  - Generating bot moves at configurable Skill Levels (1-20)
  - Evaluating board positions (centipawn scores)
  - Analysing every move in a completed game
"""

import os
import chess
import chess.engine
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MoveEvaluation:
    """Holds evaluation data for a single move."""
    move_san: str
    fen_before: str
    fen_after: str
    eval_before: float   # centipawns (from White's perspective)
    eval_after: float    # centipawns (from White's perspective)
    best_move_san: str
    score_delta: float   # negative means the move was bad for the side to move
    played_by: str       # "white" or "black"

    @property
    def classification(self) -> str:
        """Classify the quality of the move based on centipawn loss."""
        loss = abs(self.score_delta)
        if loss < 10:
            return "Best"
        elif loss < 50:
            return "Good"
        elif loss < 100:
            return "Inaccuracy"
        elif loss < 200:
            return "Mistake"
        else:
            return "Blunder"


class EngineManager:
    """Manages the Stockfish process and board state."""

    DEFAULT_TIME_LIMIT = 0.1   # seconds per engine move
    ANALYSIS_DEPTH = 18        # depth for post-game analysis

    def __init__(self, stockfish_path: str, skill_level: int = 5):
        """
        Args:
            stockfish_path: Absolute path to the Stockfish binary.
            skill_level: Stockfish Skill Level (1-20, controls playing strength).
        """
        if not os.path.isfile(stockfish_path):
            raise FileNotFoundError(
                f"Stockfish binary not found at: {stockfish_path}\n"
                "Please download it from https://stockfishchess.org/download/ "
                "and set STOCKFISH_PATH in your .env file."
            )

        self.stockfish_path = stockfish_path
        self.skill_level = min(max(skill_level, 1), 20)
        self.board = chess.Board()
        self._engine: Optional[chess.engine.SimpleEngine] = None

    # ------------------------------------------------------------------
    # Engine lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Initialise the Stockfish process."""
        self._engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        self._configure_skill()

    def stop(self) -> None:
        """Terminate the Stockfish process cleanly."""
        if self._engine:
            self._engine.quit()
            self._engine = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    # ------------------------------------------------------------------
    # Board helpers
    # ------------------------------------------------------------------

    def reset_board(self) -> None:
        """Reset to starting position."""
        self.board = chess.Board()

    def set_position(self, fen: str) -> None:
        """Load a board state from a FEN string."""
        self.board = chess.Board(fen)

    def make_move(self, uci_move: str) -> bool:
        """
        Apply a move in UCI format (e.g. 'e2e4').
        Returns True on success, False if move is illegal.
        """
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.board.legal_moves:
                self.board.push(move)
                return True
        except ValueError:
            pass
        return False

    def make_move_san(self, san_move: str) -> bool:
        """Apply a move in SAN format (e.g. 'Nf3')."""
        try:
            move = self.board.parse_san(san_move)
            self.board.push(move)
            return True
        except (ValueError, chess.AmbiguousMoveError, chess.IllegalMoveError):
            return False

    def get_fen(self) -> str:
        return self.board.fen()

    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def get_outcome(self) -> Optional[chess.Outcome]:
        return self.board.outcome()

    def get_legal_moves_uci(self) -> list[str]:
        return [m.uci() for m in self.board.legal_moves]

    # ------------------------------------------------------------------
    # Engine moves & evaluation
    # ------------------------------------------------------------------

    def get_bot_move(self, time_limit: Optional[float] = None) -> Optional[str]:
        """
        Ask Stockfish to generate the best move for the current position.
        Returns the move in SAN notation, or None if game is over.
        """
        if not self._engine or self.board.is_game_over():
            return None

        limit = chess.engine.Limit(time=time_limit or self.DEFAULT_TIME_LIMIT)
        result = self._engine.play(self.board, limit)
        if result.move:
            san = self.board.san(result.move)
            self.board.push(result.move)
            return san
        return None

    def evaluate_position(self, fen: Optional[str] = None) -> float:
        """
        Evaluate a FEN position (or current board if None).
        Returns centipawns from White's perspective.
        Mate scores use ±10000 as a sentinel.
        """
        if not self._engine:
            raise RuntimeError("Engine not started. Call start() first.")

        board = chess.Board(fen) if fen else self.board.copy()
        info = self._engine.analyse(
            board,
            chess.engine.Limit(depth=self.ANALYSIS_DEPTH)
        )
        score = info["score"].white()
        if score.is_mate():
            mate_in = score.mate()
            return 10000 if mate_in > 0 else -10000
        return float(score.score())

    def get_best_move_san(self, fen: Optional[str] = None) -> Optional[str]:
        """Return the best move in SAN notation for a given FEN (or current board)."""
        if not self._engine:
            raise RuntimeError("Engine not started. Call start() first.")

        board = chess.Board(fen) if fen else self.board.copy()
        result = self._engine.play(
            board,
            chess.engine.Limit(depth=self.ANALYSIS_DEPTH)
        )
        if result.move:
            return board.san(result.move)
        return None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_skill_level(self, level: int) -> None:
        """Adjust bot skill in real time (1-20)."""
        self.skill_level = min(max(level, 1), 20)
        if self._engine:
            self._configure_skill()

    def _configure_skill(self) -> None:
        self._engine.configure({"Skill Level": self.skill_level})

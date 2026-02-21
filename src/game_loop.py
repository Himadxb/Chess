"""
game_loop.py - Game State & Turn Management
============================================
Controls the flow of a local chess game between a human player (White)
and the Stockfish bot (Black). Records every move as a MoveRecord for
later analysis.
"""

import chess
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .engine_manager import EngineManager


@dataclass
class MoveRecord:
    """Single move record captured during a game."""
    move_number: int
    played_by: str          # "white" or "black"
    san: str                # Standard Algebraic Notation e.g. "Nf3"
    uci: str                # UCI format e.g. "g1f3"
    fen_before: str
    fen_after: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class GameLoop:
    """Manages a full chess game session."""

    def __init__(self, engine: EngineManager, player_color: chess.Color = chess.WHITE):
        self.engine = engine
        self.player_color = player_color
        self.move_history: list[MoveRecord] = []
        self._move_counter = 1
        self._started = False

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def new_game(self) -> None:
        """Reset board and history for a fresh game."""
        self.engine.reset_board()
        self.move_history = []
        self._move_counter = 1
        self._started = True

    @property
    def is_over(self) -> bool:
        return self.engine.is_game_over()

    @property
    def turn(self) -> chess.Color:
        return self.engine.board.turn

    @property
    def is_player_turn(self) -> bool:
        return self.turn == self.player_color

    def get_outcome_description(self) -> str:
        outcome = self.engine.get_outcome()
        if not outcome:
            return "Game in progress"
        winner = outcome.winner
        if winner is None:
            return f"Draw — {outcome.termination.name.replace('_', ' ').title()}"
        winner_str = "White" if winner == chess.WHITE else "Black"
        return f"{winner_str} wins — {outcome.termination.name.replace('_', ' ').title()}"

    # ------------------------------------------------------------------
    # Move processing
    # ------------------------------------------------------------------

    def apply_player_move(self, uci_move: str) -> bool:
        """
        Apply a human player's move (given in UCI format, e.g. 'e2e4').
        Records the move and returns True if successful.
        """
        if not self._started or not self.is_player_turn:
            return False

        fen_before = self.engine.get_fen()
        board = self.engine.board

        try:
            move = chess.Move.from_uci(uci_move)
            if move not in board.legal_moves:
                return False
            san = board.san(move)
            board.push(move)
        except ValueError:
            return False

        self._record_move(
            played_by="white" if self.player_color == chess.WHITE else "black",
            san=san,
            uci=uci_move,
            fen_before=fen_before,
            fen_after=self.engine.get_fen(),
        )
        return True

    def apply_bot_move(self, time_limit: Optional[float] = None) -> Optional[str]:
        """
        Ask the engine for the bot's move, apply it, record it.
        Returns the SAN of the played move or None.
        """
        if not self._started or self.is_player_turn or self.is_over:
            return None

        fen_before = self.engine.get_fen()
        board = self.engine.board

        # The engine internally pushes the move to the board via get_bot_move
        result = self.engine._engine.play(
            board, chess.engine.Limit(time=time_limit or self.engine.DEFAULT_TIME_LIMIT)
        )
        if not result.move:
            return None

        san = board.san(result.move)
        uci = result.move.uci()
        board.push(result.move)

        self._record_move(
            played_by="black" if self.player_color == chess.WHITE else "white",
            san=san,
            uci=uci,
            fen_before=fen_before,
            fen_after=self.engine.get_fen(),
        )

        if self._should_increment_counter():
            self._move_counter += 1

        return san

    # ------------------------------------------------------------------
    # Game export
    # ------------------------------------------------------------------

    def to_pgn_string(self) -> str:
        """Export the game history in a basic PGN-like text format."""
        lines = []
        i = 0
        moves = self.move_history
        while i < len(moves):
            white_move = moves[i] if moves[i].played_by == "white" else None
            black_move = moves[i + 1] if i + 1 < len(moves) else None
            move_num = (i // 2) + 1
            white_san = white_move.san if white_move else "..."
            black_san = black_move.san if black_move else ""
            lines.append(f"{move_num}. {white_san} {black_san}")
            i += 2
        return " ".join(lines)

    def save_game_json(self, path: str) -> None:
        """Persist full game data (including FEN history) to a JSON file."""
        data = {
            "outcome": self.get_outcome_description(),
            "moves": [
                {
                    "move_number": r.move_number,
                    "played_by": r.played_by,
                    "san": r.san,
                    "uci": r.uci,
                    "fen_before": r.fen_before,
                    "fen_after": r.fen_after,
                    "timestamp": r.timestamp,
                }
                for r in self.move_history
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _record_move(self, played_by: str, san: str, uci: str, fen_before: str, fen_after: str) -> None:
        self.move_history.append(
            MoveRecord(
                move_number=self._move_counter,
                played_by=played_by,
                san=san,
                uci=uci,
                fen_before=fen_before,
                fen_after=fen_after,
            )
        )

    def _should_increment_counter(self) -> bool:
        """Increment full-move counter after Black's move."""
        return len(self.move_history) % 2 == 0

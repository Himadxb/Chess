"""
analyzer.py - Post-Game Analysis & Blunder Detection
=====================================================
Processes a completed game's MoveRecord list against the Stockfish engine
to compute centipawn evaluation deltas, best moves, and classify each
move (Best, Good, Inaccuracy, Mistake, Blunder).
"""

import chess
from dataclasses import dataclass
from typing import Optional
from .engine_manager import EngineManager, MoveEvaluation
from .game_loop import MoveRecord


@dataclass
class GameReport:
    """Full analysis report for a completed game."""
    evaluated_moves: list[MoveEvaluation]
    total_moves: int
    player_color: str

    @property
    def player_moves(self) -> list[MoveEvaluation]:
        return [m for m in self.evaluated_moves if m.played_by == self.player_color]

    @property
    def blunders(self) -> list[MoveEvaluation]:
        return [m for m in self.player_moves if m.classification == "Blunder"]

    @property
    def mistakes(self) -> list[MoveEvaluation]:
        return [m for m in self.player_moves if m.classification == "Mistake"]

    @property
    def inaccuracies(self) -> list[MoveEvaluation]:
        return [m for m in self.player_moves if m.classification == "Inaccuracy"]

    @property
    def accuracy_percentage(self) -> float:
        """
        Simple accuracy metric: percentage of player moves that are
        Best or Good (centipawn loss < 50).
        """
        if not self.player_moves:
            return 0.0
        good = sum(
            1 for m in self.player_moves
            if m.classification in ("Best", "Good")
        )
        return round(good / len(self.player_moves) * 100, 1)

    def summary_stats(self) -> dict:
        return {
            "total_player_moves": len(self.player_moves),
            "blunders": len(self.blunders),
            "mistakes": len(self.mistakes),
            "inaccuracies": len(self.inaccuracies),
            "accuracy": f"{self.accuracy_percentage}%",
        }

    def get_critical_moments(self, top_n: int = 3) -> list[MoveEvaluation]:
        """
        Return the top N most significant player mistakes/blunders sorted
        by centipawn loss (worst first).
        """
        bad_moves = [
            m for m in self.player_moves
            if m.classification in ("Mistake", "Blunder")
        ]
        return sorted(bad_moves, key=lambda m: abs(m.score_delta), reverse=True)[:top_n]


class Analyzer:
    """Runs post-game analysis using Stockfish."""

    ANALYSIS_DEPTH = 18

    def __init__(self, engine: EngineManager):
        self.engine = engine

    def analyse_game(
        self,
        move_history: list[MoveRecord],
        player_color: str = "white",
    ) -> GameReport:
        """
        Analyse every move in the recorded history.
        Returns a GameReport with full MoveEvaluation objects.
        """
        evaluated_moves: list[MoveEvaluation] = []

        for record in move_history:
            eval_before = self._evaluate_fen(record.fen_before)
            eval_after = self._evaluate_fen(record.fen_after)
            best_move = self._best_move_for_fen(record.fen_before)

            # From the perspective of the side that moved, a drop in eval is bad.
            if record.played_by == "white":
                delta = eval_after - eval_before   # positive = good for White
            else:
                delta = eval_before - eval_after   # positive = good for Black

            evaluated_moves.append(
                MoveEvaluation(
                    move_san=record.san,
                    fen_before=record.fen_before,
                    fen_after=record.fen_after,
                    eval_before=eval_before,
                    eval_after=eval_after,
                    best_move_san=best_move or "?",
                    score_delta=delta,
                    played_by=record.played_by,
                )
            )

        return GameReport(
            evaluated_moves=evaluated_moves,
            total_moves=len(move_history),
            player_color=player_color,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evaluate_fen(self, fen: str) -> float:
        """Evaluate a FEN string via Stockfish, returning centipawns (White POV)."""
        board = chess.Board(fen)
        info = self.engine._engine.analyse(
            board,
            chess.engine.Limit(depth=self.ANALYSIS_DEPTH),
        )
        score = info["score"].white()
        if score.is_mate():
            return 10000 if score.mate() > 0 else -10000
        return float(score.score())

    def _best_move_for_fen(self, fen: str) -> Optional[str]:
        """Return the best move in SAN notation for a given FEN."""
        board = chess.Board(fen)
        result = self.engine._engine.play(
            board,
            chess.engine.Limit(depth=self.ANALYSIS_DEPTH),
        )
        if result.move:
            return board.san(result.move)
        return None

    @staticmethod
    def infer_game_phase(fen: str) -> str:
        """
        Heuristic game phase detection from piece count.
        Returns 'Opening', 'Middlegame', or 'Endgame'.
        """
        board = chess.Board(fen)
        piece_count = len(board.piece_map())
        queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + \
                 len(board.pieces(chess.QUEEN, chess.BLACK))

        if piece_count >= 28:
            return "Opening"
        elif piece_count <= 12 or queens == 0:
            return "Endgame"
        else:
            return "Middlegame"

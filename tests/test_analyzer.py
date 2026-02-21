"""
test_analyzer.py - Unit tests for the Analyzer & GameReport
"""
import chess
import pytest
from unittest.mock import MagicMock, patch
from src.analyzer import Analyzer, GameReport
from src.engine_manager import MoveEvaluation
from src.game_loop import MoveRecord


def make_eval(delta: float, played_by: str = "white") -> MoveEvaluation:
    return MoveEvaluation(
        move_san="e4", fen_before=chess.Board().fen(), fen_after=chess.Board().fen(),
        eval_before=0, eval_after=delta, best_move_san="d4",
        score_delta=delta, played_by=played_by,
    )


class TestGameReport:
    def test_accuracy_all_good(self):
        evals = [make_eval(5), make_eval(30), make_eval(10)]
        report = GameReport(evaluated_moves=evals, total_moves=3, player_color="white")
        assert report.accuracy_percentage == 100.0

    def test_accuracy_mixed(self):
        evals = [make_eval(5), make_eval(-300)]   # 1 good, 1 blunder
        report = GameReport(evaluated_moves=evals, total_moves=2, player_color="white")
        assert report.accuracy_percentage == 50.0

    def test_blunders_counted(self):
        evals = [make_eval(-300), make_eval(-5)]
        report = GameReport(evaluated_moves=evals, total_moves=2, player_color="white")
        assert len(report.blunders) == 1

    def test_critical_moments_sorted_by_loss(self):
        evals = [make_eval(-100), make_eval(-300), make_eval(-200)]
        report = GameReport(evaluated_moves=evals, total_moves=3, player_color="white")
        cm = report.get_critical_moments(top_n=3)
        # Should be sorted worst first
        losses = [abs(m.score_delta) for m in cm]
        assert losses == sorted(losses, reverse=True)

    def test_player_moves_filter(self):
        evals = [make_eval(5, "white"), make_eval(-100, "black")]
        report = GameReport(evaluated_moves=evals, total_moves=2, player_color="white")
        assert len(report.player_moves) == 1

    def test_summary_stats_keys(self):
        report = GameReport(evaluated_moves=[make_eval(5)], total_moves=1, player_color="white")
        stats = report.summary_stats()
        assert set(stats.keys()) == {"total_player_moves", "blunders", "mistakes", "inaccuracies", "accuracy"}


class TestAnalyzerGamePhase:
    def test_opening_phase(self):
        # Starting position has 32 pieces
        phase = Analyzer.infer_game_phase(chess.Board().fen())
        assert phase == "Opening"

    def test_endgame_few_pieces(self):
        # Near-endgame position: only kings and a couple pawns
        board = chess.Board("8/8/3k4/8/8/3K4/P7/8 w - - 0 1")
        phase = Analyzer.infer_game_phase(board.fen())
        assert phase == "Endgame"

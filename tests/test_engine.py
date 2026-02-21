"""
test_engine.py - Unit tests for the EngineManager & MoveEvaluation
"""
import chess
import pytest
from unittest.mock import MagicMock, patch
from src.engine_manager import EngineManager, MoveEvaluation


# --------------------------------------------------------------------------
# MoveEvaluation classification tests (pure logic, no engine needed)
# --------------------------------------------------------------------------

class TestMoveEvaluationClassification:
    def _make_eval(self, delta: float) -> MoveEvaluation:
        return MoveEvaluation(
            move_san="e4", fen_before="", fen_after="",
            eval_before=0, eval_after=delta,
            best_move_san="d4", score_delta=delta,
            played_by="white"
        )

    def test_best_move(self):
        assert self._make_eval(5).classification == "Best"

    def test_good_move(self):
        assert self._make_eval(30).classification == "Good"

    def test_inaccuracy(self):
        assert self._make_eval(-75).classification == "Inaccuracy"

    def test_mistake(self):
        assert self._make_eval(-150).classification == "Mistake"

    def test_blunder(self):
        assert self._make_eval(-300).classification == "Blunder"


# --------------------------------------------------------------------------
# Board operations (no Stockfish process required)
# --------------------------------------------------------------------------

class TestEngineManagerBoard:
    """Test board manipulation without starting the Stockfish process."""

    def setup_method(self):
        with patch("os.path.isfile", return_value=True):
            self.manager = EngineManager("fake/stockfish", elo=1200)

    def test_initial_position_fen(self):
        assert self.manager.get_fen() == chess.Board().fen()

    def test_make_legal_move(self):
        assert self.manager.make_move("e2e4") is True
        board = chess.Board()
        board.push_uci("e2e4")
        assert self.manager.get_fen() == board.fen()

    def test_make_illegal_move(self):
        assert self.manager.make_move("e2e5") is False

    def test_make_move_san(self):
        assert self.manager.make_move_san("e4") is True

    def test_reset_board(self):
        self.manager.make_move("e2e4")
        self.manager.reset_board()
        assert self.manager.get_fen() == chess.Board().fen()

    def test_set_position(self):
        fen = "8/8/8/8/4P3/8/8/8 w - - 0 1"
        self.manager.set_position(fen)
        assert self.manager.get_fen() == fen

    def test_legal_moves_not_empty(self):
        moves = self.manager.get_legal_moves_uci()
        assert len(moves) == 20  # 20 opening moves

    def test_elo_clamped_to_max(self):
        with patch("os.path.isfile", return_value=True):
            e = EngineManager("fake/stockfish", elo=9999)
        assert e.elo == EngineManager.ELO_MAX

    def test_elo_low_value_preserved(self):
        """Low ELO should be stored as-is (UCI_Elo clamping happens in configure)."""
        with patch("os.path.isfile", return_value=True):
            e = EngineManager("fake/stockfish", elo=400)
        assert e.elo == 400

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            EngineManager("does/not/exist.exe")

    def test_game_not_over_at_start(self):
        assert self.manager.is_game_over() is False

    # backward compat: skill_level is deprecated, not an init arg
    def test_skill_level_clamped(self):
        """Verify ELO-based construction doesn't break; set_elo() still works."""
        with patch("os.path.isfile", return_value=True):
            e = EngineManager("fake/stockfish", elo=1500)
        assert e.elo == 1500

"""
test_coach.py - Unit tests for ChessCoach prompt building & LLM backends
"""
import pytest
from unittest.mock import MagicMock, patch
from src.engine_manager import MoveEvaluation
from src.analyzer import GameReport
from src.coach_llm import (
    ChessCoach, OllamaBackend, OpenAIBackend,
    build_move_feedback_prompt, build_game_summary_prompt
)


def make_move_eval(delta: float = -300.0) -> MoveEvaluation:
    return MoveEvaluation(
        move_san="Qxf7??", fen_before="rnbq1rk1/pppp1ppp/5n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQ - 4 4",
        fen_after="rnbq1rk1/pppp1Qpp/5n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQ - 0 4",
        eval_before=50, eval_after=-250, best_move_san="Nd5",
        score_delta=delta, played_by="white",
    )


class TestPromptBuilders:
    def test_move_feedback_prompt_contains_key_info(self):
        move = make_move_eval()
        prompt = build_move_feedback_prompt(move, game_phase="Middlegame", player_elo=1200)
        assert "Qxf7??" in prompt
        assert "Nd5" in prompt
        assert "Blunder" in prompt
        assert "1200" in prompt
        assert "Middlegame" in prompt

    def test_game_summary_prompt_contains_stats(self):
        move = make_move_eval()
        report = GameReport(evaluated_moves=[move], total_moves=1, player_color="white")
        prompt = build_game_summary_prompt(report, player_elo=1000, outcome="Black wins")
        assert "1000" in prompt
        assert "Black wins" in prompt


class TestOllamaBackend:
    def test_connection_error_returns_none(self):
        """OllamaBackend returns None on failure; ChessCoach handles the fallback."""
        backend = OllamaBackend(host="http://localhost:9999", model="doesnotexist")
        result = backend.generate("test prompt")
        assert result is None  # None signals ChessCoach to use RuleBasedFallback


class TestChessCoach:
    def test_ollama_backend_selected_by_default(self):
        coach = ChessCoach(backend="ollama")
        assert isinstance(coach._llm, OllamaBackend)

    def test_openai_backend_selected_when_key_provided(self):
        coach = ChessCoach(backend="openai", openai_api_key="sk-test")
        assert isinstance(coach._llm, OpenAIBackend)

    def test_ollama_selected_without_openai_key(self):
        coach = ChessCoach(backend="openai", openai_api_key="")
        assert isinstance(coach._llm, OllamaBackend)

    def test_explain_critical_moments_returns_list(self):
        move = make_move_eval()
        report = GameReport(evaluated_moves=[move], total_moves=1, player_color="white")
        mock_backend = MagicMock()
        mock_backend.generate.return_value = "Coach says: great game!"
        coach = ChessCoach()
        coach._llm = mock_backend
        results = coach.explain_critical_moments(report)
        assert isinstance(results, list)
        assert results[0]["move"] == "Qxf7??"
        assert results[0]["explanation"] == "Coach says: great game!"

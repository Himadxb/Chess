"""
coach_llm.py - LLM Coaching & Explanation Layer
=================================================
Interfaces with a Large Language Model (Ollama local or OpenAI API)
to generate human-readable chess coaching feedback.

The LLM is used ONLY as an explanation layer. All chess logic
(move generation, evaluation) is handled by Stockfish.
"""

import os
import json
import requests
from typing import Optional
from .engine_manager import MoveEvaluation
from .analyzer import GameReport, Analyzer


# --------------------------------------------------------------------------
# Prompt builders
# --------------------------------------------------------------------------

def build_move_feedback_prompt(
    move: MoveEvaluation,
    game_phase: str,
    player_elo: int = 1000,
) -> str:
    """Build a focused prompt for a single critical move."""
    return f"""You are an expert chess coach giving feedback to a {player_elo}-ELO player.

Game phase: {game_phase}
Move played: {move.move_san} ({move.classification})
Best move was: {move.best_move_san}
Evaluation before: {move.eval_before:.0f} centipawns (White's perspective)
Evaluation after: {move.eval_after:.0f} centipawns
Centipawn loss: {abs(move.score_delta):.0f}

Explain in 2-4 clear sentences WHY this move was a {move.classification.lower()}, what threat or tactic was missed, and what the player should have considered instead. Be encouraging but educational. Do NOT use chess jargon without brief explanation.
"""


def build_game_summary_prompt(
    report: GameReport,
    player_elo: int,
    outcome: str,
) -> str:
    """Build a whole-game coaching summary prompt."""
    stats = report.summary_stats()
    critical = report.get_critical_moments(top_n=3)

    critical_detail = "\n".join(
        f"  - Move {m.move_san} (lost ~{abs(m.score_delta):.0f} cp, best was {m.best_move_san})"
        for m in critical
    )

    return f"""You are an expert chess coach. A {player_elo}-ELO player just finished a game.

Outcome: {outcome}
Player accuracy: {stats['accuracy']}
Blunders: {stats['blunders']}, Mistakes: {stats['mistakes']}, Inaccuracies: {stats['inaccuracies']}

Top {len(critical)} critical moments:
{critical_detail}

Write a warm, encouraging post-game summary (5-8 sentences) that:
1. Acknowledges the outcome and overall performance.
2. Highlights the most important lesson from the biggest mistake.
3. Gives 1-2 concrete strategic tips to improve.
Keep the language accessible for a {player_elo}-ELO player.
"""


# --------------------------------------------------------------------------
# LLM backends
# --------------------------------------------------------------------------

class OllamaBackend:
    """Calls a locally running Ollama server."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3"):
        self.host = host.rstrip("/")
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.ConnectionError:
            return (
                "[Ollama is not running. Start it with `ollama serve` and "
                f"ensure model '{self.model}' is available via `ollama pull {self.model}`.]"
            )
        except Exception as e:
            return f"[LLM Error: {e}]"


class OpenAIBackend:
    """Calls the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful and encouraging chess coach."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            return "[openai package not installed. Run: pip install openai]"
        except Exception as e:
            return f"[OpenAI Error: {e}]"


# --------------------------------------------------------------------------
# Coach interface
# --------------------------------------------------------------------------

class ChessCoach:
    """
    High-level coaching interface that selects the right LLM backend
    based on environment config and generates coaching feedback.
    """

    def __init__(
        self,
        backend: str = "ollama",
        player_elo: int = 1000,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llama3",
        openai_api_key: str = "",
        openai_model: str = "gpt-4o-mini",
    ):
        self.player_elo = player_elo
        if backend == "openai" and openai_api_key:
            self._llm = OpenAIBackend(api_key=openai_api_key, model=openai_model)
        else:
            self._llm = OllamaBackend(host=ollama_host, model=ollama_model)

    @classmethod
    def from_env(cls) -> "ChessCoach":
        """Construct a ChessCoach from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        return cls(
            backend=os.getenv("LLM_BACKEND", "ollama"),
            player_elo=int(os.getenv("PLAYER_ELO", "1000")),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

    def explain_move(self, move: MoveEvaluation, fen: str) -> str:
        """Generate coaching feedback for a single critical move."""
        phase = Analyzer.infer_game_phase(fen)
        prompt = build_move_feedback_prompt(move, game_phase=phase, player_elo=self.player_elo)
        return self._llm.generate(prompt)

    def generate_game_summary(self, report: GameReport, outcome: str) -> str:
        """Generate a full post-game coaching summary."""
        prompt = build_game_summary_prompt(report, self.player_elo, outcome)
        return self._llm.generate(prompt, max_tokens=800)

    def explain_critical_moments(self, report: GameReport) -> list[dict]:
        """
        Return a list of dicts with move info + LLM explanation
        for the top critical moments.
        """
        results = []
        for move in report.get_critical_moments(top_n=3):
            explanation = self.explain_move(move, move.fen_before)
            results.append({
                "move": move.move_san,
                "classification": move.classification,
                "best_move": move.best_move_san,
                "centipawn_loss": abs(move.score_delta),
                "explanation": explanation,
            })
        return results

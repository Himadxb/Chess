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
            self._try_start_ollama()
            return None  # signal: use rule-based fallback
        except Exception as e:
            return None  # signal: use rule-based fallback


    def _try_start_ollama(self) -> None:
        """
        Attempt to pull the model and start Ollama in the background.
        Only runs once per session.
        """
        import threading, subprocess
        if getattr(self, "_ollama_start_attempted", False):
            return
        self._ollama_start_attempted = True

        def _run():
            try:
                # Pull the model (no-op if already present)
                subprocess.run(
                    ["ollama", "pull", self.model],
                    timeout=300, capture_output=True
                )
                # Start the ollama server in background
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (FileNotFoundError, Exception):
                pass  # ollama not installed — ignore silently

        threading.Thread(target=_run, daemon=True).start()


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
        except (ImportError, Exception):
            return None  # signal: use rule-based fallback



class RuleBasedFallback:
    """
    Always-available coaching summary generated purely from GameReport data.
    Used when no LLM backend is reachable.
    """

    @staticmethod
    def game_summary(report: "GameReport", outcome: str, player_elo: int) -> str:
        stats = report.summary_stats()
        acc   = stats["accuracy"]
        blunders    = stats["blunders"]
        mistakes    = stats["mistakes"]
        inaccuracies= stats["inaccuracies"]
        critical = report.get_critical_moments(top_n=1)

        lines = [
            f"Game Over: {outcome}",
            f"",
            f"Your accuracy this game: {acc}",
            f"  • Blunders: {blunders}   Mistakes: {mistakes}   Inaccuracies: {inaccuracies}",
            f"",
        ]

        if critical:
            m = critical[0]
            phase = Analyzer.infer_game_phase(m.fen_before)
            lines += [
                f"Most critical moment [{phase}]: {m.move_san} ({m.classification})",
                f"  Centipawn loss: {min(abs(m.score_delta), 999):.0f}{'+ (decisive)' if abs(m.score_delta) > 999 else ''} cp",
                f"  Engine suggested: {m.best_move_san} instead.",
                f"",
            ]

        # General tips based on stats
        if blunders >= 3:
            lines.append("📌 Tip: You had several blunders. Before each move, ask — does this leave a piece hanging?")
        elif mistakes >= 3:
            lines.append("📌 Tip: A few mistakes cost you. Try to calculate at least 2 moves ahead before committing.")
        elif float(acc.rstrip('%')) >= 70:
            lines.append("📌 Well played! Your accuracy was strong. Focus on converting advantages in the endgame.")
        else:
            lines.append("📌 Keep practising — consistency comes with time. Review the critical moments above.")

        # Ollama auto-starts in background — no nag message needed
        lines.append("")
        lines.append("💡 AI coaching via Ollama will activate automatically on the next game.")
        return "\n".join(lines)

    @staticmethod
    def move_explanation(move: "MoveEvaluation", phase: str) -> str:
        loss = abs(move.score_delta)
        return (
            f"{move.classification} in the {phase}: {move.move_san} "
            f"(lost ~{loss:.0f} cp). "
            f"Engine preferred: {move.best_move_san}."
        )



# --------------------------------------------------------------------------
# LiveCoach — instant rule-based in-game tips (no LLM, no latency)
# --------------------------------------------------------------------------

class LiveCoach:
    """
    Generates instant coaching tips during the game based on:
    - Move number (opening principles)
    - Board state (material, pawn structure)
    - Last move quality
    No engine calls — purely deterministic and instant.
    """

    OPENING_TIPS = [
        "Opening principle: Control the centre with pawns to e4 or d4.",
        "Opening principle: Develop your knights and bishops early.",
        "Opening principle: Castle early to keep your king safe.",
        "Opening principle: Don't move the same piece twice in the opening.",
        "Opening principle: Connect your rooks by castling and developing all pieces.",
        "Opening principle: Avoid moving your queen too early — it can be attacked.",
        "Opening principle: Each move should develop a piece or improve your position.",
        "Tip: Look for forks — moves that attack two pieces at once.",
    ]

    MIDDLEGAME_TIPS = [
        "Middlegame tip: Before moving, ask — can my opponent capture anything for free?",
        "Middlegame tip: Identify your opponent's most dangerous piece and neutralise it.",
        "Middlegame tip: Look for checks, captures, and threats before making a quiet move.",
        "Middlegame tip: Rooks belong on open files — move pawns to open lines for them.",
        "Middlegame tip: Knights are strongest in the centre; bishops on open diagonals.",
        "Middlegame tip: Double-check — will this move leave a piece undefended?",
        "Middlegame tip: Look for outpost squares — squares where your knight can't be chased.",
        "Middlegame tip: Coordinate your pieces — two pieces working together beat one powerful one.",
    ]

    ENDGAME_TIPS = [
        "Endgame tip: Activate your king — it's a powerful piece in the endgame.",
        "Endgame tip: Push passed pawns toward promotion.",
        "Endgame tip: The rook is most powerful behind a passed pawn.",
        "Endgame tip: In king + pawn endgames, opposition is key.",
        "Endgame tip: Eliminate your opponent's passed pawns early.",
    ]

    @classmethod
    def tip(cls, board, move_count: int, last_move=None) -> str:
        import chess
        piece_count = len(board.piece_map())

        if piece_count >= 26 or move_count <= 14:
            phase = "Opening"
            tips = cls.OPENING_TIPS
        elif piece_count <= 12:
            phase = "Endgame"
            tips = cls.ENDGAME_TIPS
        else:
            phase = "Middlegame"
            tips = cls.MIDDLEGAME_TIPS

        import hashlib
        tip_idx = int(hashlib.md5(str(move_count).encode()).hexdigest(), 16) % len(tips)
        tip = tips[tip_idx]

        # Add threat detection bonus
        extra = ""
        if board.is_check():
            extra = "\n⚠️ Your king is in check! Find a safe square."
        elif board.is_attacked_by(board.turn, board.king(not board.turn)):
            # We're giving check
            extra = "\n♟️ You're giving check — look for follow-up tactics."
        elif last_move and last_move.played_by == "white":
            # Check if any white piece is hanging
            for sq, piece in board.piece_map().items():
                if piece.color == chess.WHITE:
                    if board.is_attacked_by(chess.BLACK, sq) and not board.is_attacked_by(chess.WHITE, sq):
                        pname = chess.piece_name(piece.piece_type).capitalize()
                        extra = f"\n⚠️ Danger: your {pname} on {chess.square_name(sq)} may be undefended!"
                        break

        return f"[{phase}] {tip}{extra}"


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
        result = self._llm.generate(prompt) if self._llm else None
        if result is None:
            return RuleBasedFallback.move_explanation(move, phase)
        return result

    def generate_game_summary(self, report: GameReport, outcome: str) -> str:
        """Generate a full post-game coaching summary."""
        prompt = build_game_summary_prompt(report, self.player_elo, outcome)
        result = self._llm.generate(prompt, max_tokens=800) if self._llm else None
        if result is None:
            return RuleBasedFallback.game_summary(report, outcome, self.player_elo)
        return result

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

"""
main.py - Application Entry Point
===================================
Loads environment config, starts the Stockfish engine, and launches
the PyQt6 Chess Coach Desktop application.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to allow `src.*` imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine_manager import EngineManager
from src.coach_llm import ChessCoach
from src.app_gui import launch_app


def main():
    # Load .env from the project root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        print("⚠️  No .env file found. Copy .env.example to .env and configure it.")
        print(f"   Expected path: {env_path}\n")

    stockfish_path = os.getenv("STOCKFISH_PATH", "stockfish/stockfish.exe")
    bot_elo        = int(os.getenv("BOT_ELO", "1200"))

    print("♟️  ChessC+ — AI Chess Coach")
    print(f"   Stockfish path : {stockfish_path}")
    print(f"   Bot ELO        : {bot_elo}")
    print(f"   LLM backend    : {os.getenv('LLM_BACKEND', 'ollama')}\n")

    try:
        engine = EngineManager(stockfish_path=stockfish_path, elo=bot_elo)
        engine.start()
    except FileNotFoundError as e:
        print(f"\n❌  {e}")
        print("\nTo fix this:")
        print("  1. Download Stockfish: https://stockfishchess.org/download/")
        print("  2. Place the binary at the path above (or update STOCKFISH_PATH in .env)")
        sys.exit(1)

    coach = ChessCoach.from_env()

    try:
        launch_app(engine, coach)
    finally:
        engine.stop()
        print("\nEngine stopped. Goodbye!")


if __name__ == "__main__":
    main()

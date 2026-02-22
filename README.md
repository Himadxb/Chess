# ♟️ ChessC+ — AI Chess Coach

A local Python chess application where you play against a Stockfish-powered bot and receive real-time and post-game coaching feedback.

---

## Features

- **Play vs. Bot** — Stockfish engine with ELO-based difficulty (400–2800, default 1200)
- **Live Coaching** — instant tips after every move (Opening / Middlegame / Endgame principles, hanging-piece alerts)
- **Post-Game Analysis** — centipawn accuracy, blunder/mistake/inaccuracy counts, critical moment replay
- **AI Coach Panel** — powered by local Ollama (llama3) or OpenAI; auto-starts Ollama if installed
- **Evaluation Bar** — live position evaluation updated in the background after each move
- **Modern GUI** — PyQt6 board with cream/green squares, click-to-move, flip board, move history
- **ELO Slider** — set bot strength to Beginner → Master GM in the sidebar
- **Unit Tested** — 32 tests covering engine, analysis, and coaching modules

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Himadxb/Chess.git
cd Chess

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. Configure
copy .env.example .env
# Edit .env — set STOCKFISH_PATH

# 4. Run
python src/main.py
```

### Stockfish

Download from [stockfishchess.org/download](https://stockfishchess.org/download/) and place at:

```
stockfish/stockfish-windows-x86-64-avx2.exe
```

### AI Coaching (optional)

```bash
ollama pull llama3    # ~4 GB, one-time
ollama serve          # starts automatically if installed
```

If Ollama isn't running, the app falls back to rule-based coaching automatically.

---

## Project Structure

```
ChessC+/
├── src/
│   ├── main.py             # Entry point
│   ├── engine_manager.py   # Stockfish wrapper (ELO, eval, bot moves)
│   ├── game_loop.py        # Turn management, PGN / JSON export
│   ├── analyzer.py         # Post-game centipawn analysis
│   ├── coach_llm.py        # LLM coaching + LiveCoach (instant tips)
│   ├── app_gui.py          # PyQt6 board, click-to-move, game flow
│   └── ui_components.py    # Eval bar, move history, coaching panel
├── tests/                  # 32 unit tests
├── .env.example
└── requirements.txt
```

---

## Environment Variables

| Variable         | Default                                       | Description                                 |
| ---------------- | --------------------------------------------- | ------------------------------------------- |
| `STOCKFISH_PATH` | `stockfish/stockfish-windows-x86-64-avx2.exe` | Path to Stockfish binary                    |
| `BOT_ELO`        | `1200`                                        | Bot strength (400–2800)                     |
| `LLM_BACKEND`    | `ollama`                                      | `ollama` or `openai`                        |
| `OLLAMA_HOST`    | `http://localhost:11434`                      | Ollama server URL                           |
| `OLLAMA_MODEL`   | `llama3`                                      | Model name                                  |
| `OPENAI_API_KEY` | —                                             | OpenAI key (if using OpenAI backend)        |
| `PLAYER_ELO`     | `1000`                                        | Your approximate ELO (for coaching context) |

---

## Running Tests

```bash
python run_tests.py
# 32 passed in ~4.5s
```

---

## Tech Stack

- **Python 3.11+**
- **python-chess** — move validation, PGN, board representation
- **Stockfish** — engine (UCI protocol via `chess.engine`)
- **PyQt6** — desktop GUI
- **Ollama / OpenAI** — LLM coaching backend
- **pytest** — unit testing

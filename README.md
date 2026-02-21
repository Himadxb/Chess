# ♟️ Chess AI Coach (ChessC+)

A Python-based local **Chess AI Coach and Play Engine** that lets you play full games against a configurable Stockfish bot while delivering deep post-game analysis and human-readable coaching feedback powered by an LLM.

---

## ✨ Features

| Feature                 | Description                                               |
| ----------------------- | --------------------------------------------------------- |
| 🤖 Configurable Bot     | Play against Stockfish at any difficulty (ELO-calibrated) |
| 📊 Post-Game Analysis   | Move-by-move evaluation, blunder & inaccuracy detection   |
| 🧠 AI Coaching          | LLM-generated explanations for mistakes & key moments     |
| 🖥️ Modern Desktop GUI   | PyQt6 interface with evaluation bar and move history      |
| 🔌 Flexible LLM Backend | Supports local Ollama models and OpenAI API               |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Stockfish](https://stockfishchess.org/download/): Download and place the binary at `stockfish/stockfish.exe` (Windows) or `stockfish/stockfish` (Linux/macOS).
- [Ollama](https://ollama.ai) (optional, for local LLM coaching)

### Installation

```bash
# Clone the repo
git clone https://github.com/Himadxb/Chess.git
cd Chess

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:

```
STOCKFISH_PATH=stockfish/stockfish.exe
LLM_BACKEND=ollama           # or "openai"
OLLAMA_MODEL=llama3
OPENAI_API_KEY=sk-...        # Only needed if LLM_BACKEND=openai
```

### Running

```bash
python src/main.py
```

---

## 📁 Project Structure

```
ChessC+/
├── src/
│   ├── main.py            # Entry point
│   ├── engine_manager.py  # Stockfish integration & bot logic
│   ├── game_loop.py       # Game state & turn management
│   ├── analyzer.py        # Post-game analysis & blunder detection
│   ├── coach_llm.py       # LLM coaching & prompt engineering
│   ├── app_gui.py         # PyQt6 GUI (board rendering)
│   └── ui_components.py   # Sidebar, eval bar, coach panel
├── assets/
│   └── pieces/            # SVG chess piece images
├── tests/
│   ├── test_engine.py
│   ├── test_analyzer.py
│   └── test_coach.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧠 LLM Architecture

The LLM is used **only as an explanation layer**, not for move generation. Stockfish handles all deterministic chess logic. The LLM receives structured data:

- Move played vs. optimal move (in algebraic notation)
- Centipawn evaluation before and after
- Game phase (opening/middlegame/endgame)
- Player's approximate ELO rating

This generates contextual coaching feedback like: _"In this position, your Qxf7?? blundered a queen. Stockfish suggested Nd5 instead, which would have forked the rook and king, winning a full piece."_

---

## 🛣️ Roadmap

- [x] Project Setup & Architecture
- [ ] Core Board & Engine Integration
- [ ] Desktop GUI (PyQt6)
- [ ] Post-Game Analyzer
- [ ] LLM Coaching Layer
- [ ] Fine-tuning pipeline (LoRA)

---

## 📄 License

MIT License

# D&D 5e Combat Simulator

Modular, LLM-driven D&D 5e combat simulator bridging **Gemini DM** (storytelling) with a **HoMM3-style 2D grid combat client**.

## Stack
- **Backend**: FastAPI + Pydantic v2 + uvicorn
- **Client** (Phase 2): React + Phaser 3
- **LLM** (Phase 4): Gemini function calling

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload --port 8000
python -m pytest tests/test_pipeline.py -v
```

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Foundation | ✅ Done | Mono-repo, Pydantic schemas, mock service, state store |
| 1 — Combat Engine | ✅ Done | D&D 5e rules: initiative, attack, damage |
| 2 — Visual Client | 🔜 Next | Phaser 3 grid renderer |
| 3 — WebSocket Bridge | 🔜 | SSE real-time sync |
| 4 — Gemini DM | 🔜 | Real function calling integration |
| 5 — Polish | 🔜 | Docker, demo mode, CI/CD |

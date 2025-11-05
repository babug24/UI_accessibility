VINX ULTRA — Local demo scaffold

What this is
- A minimal, local demo scaffold of "VINX ULTRA":
  - Python FastAPI backend that serves a simple blue/white frontend
  - Streaming chat endpoint (simulated streaming)
  - Placeholder image generation endpoint (SVG) — ready to wire to real image APIs
  - Table rendering in chat
  - Simple SVG AI symbol next to the name `VINX ULTRA`

Important notes
- This scaffold uses placeholder/local behavior by default.
- To connect to real LLMs (Anthropic Claude Sonnet 7 / OpenAI), set environment variables and integrate the provider-specific client code (I can add this once you provide keys).

Quick start (Windows cmd.exe)
1. Create a virtual environment and install deps:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Run the app:

   set UVICORN_CMD=uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
   %UVICORN_CMD%

3. Open http://127.0.0.1:8000 in your browser.

Next steps I can do for you
- Integrate Claude Sonnet 7 using an Anthropic API key you provide.
- Hook up a real image generation API (Stable Diffusion / DALL·E / Replicate).
- Add streaming with WebSockets for lower latency.
- Add user accounts, history, and export.

If you want me to proceed to any of the above, tell me which and provide any API keys or confirm you want local-only.

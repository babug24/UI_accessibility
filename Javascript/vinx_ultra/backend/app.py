from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
import asyncio
import os
import json

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="VINX ULTRA Demo")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))

# Adapter imports
from adapters import model_adapter, generate_image
from moderation import check_text_allowed
from db import init_db, save_message, get_history

# Initialize DB (creates file if needed)
try:
    init_db()
except Exception:
    # Not fatal for demo
    pass

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    tpl = env.get_template("index.html")
    html = tpl.render()
    return HTMLResponse(content=html)


@app.post("/api/chat")
async def chat(message: str = Form(...)):
    """Non-streaming endpoint returning JSON (for basic uses)"""
    allowed, reason = check_text_allowed(message)
    if not allowed:
        return JSONResponse(content={"type": "error", "error": "message blocked", "reason": reason}, status_code=400)

    resp = await model_adapter.generate_response(message)
    # persist
    try:
        save_message('user', message)
        save_message('vinx', json.dumps(resp))
    except Exception:
        pass
    return JSONResponse(content=resp)


@app.post("/api/chat/stream")
async def chat_stream(message: str = Form(...)):
    """Streaming endpoint using Server-Sent Events (SSE) style chunks with text/event-stream.
    Streams JSON chunks produced by the adapter (each chunk is JSON string)"""

    allowed, reason = check_text_allowed(message)
    if not allowed:
        return JSONResponse(content={"type": "error", "error": "message blocked", "reason": reason}, status_code=400)

    async def event_generator(prompt: str):
        async for chunk in model_adapter.stream_response(prompt):
            # Each chunk is a JSON string like {type: 'delta', text: '...'}
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0)
        # final done is the adapter's responsibility

    # persist user message
    try:
        save_message('user', message)
    except Exception:
        pass

    return StreamingResponse(event_generator(message), media_type="text/event-stream")


@app.get("/api/history")
async def history():
    try:
        h = get_history(500)
        return JSONResponse(content=h)
    except Exception:
        return JSONResponse(content=[], status_code=200)


@app.post("/api/generate_image")
async def generate_image_endpoint(prompt: str = Form(...)):
    """Image generation endpoint. Uses image adapter if configured; otherwise returns placeholder."""
    allowed, reason = check_text_allowed(prompt)
    if not allowed:
        return JSONResponse(content={"error": "prompt blocked", "reason": reason}, status_code=400)

    img = await generate_image(prompt)
    # persist
    try:
        save_message('user', prompt)
        save_message('vinx', json.dumps({'type': 'image', 'payload': img}))
    except Exception:
        pass
    return JSONResponse(content=img)


@app.get("/api/ping")
async def ping():
    return JSONResponse(content={"ok": True, "service": "vinx-ultra-demo"})


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat. Client should send a JSON message
    like {"prompt":"..."} as the first message, then the server will stream
    JSON chunks (one per WebSocket message) produced by model_adapter.stream_response.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        try:
            obj = json.loads(data)
            prompt = obj.get('prompt') or obj.get('message') or ''
        except Exception:
            prompt = data

        allowed, reason = check_text_allowed(prompt)
        if not allowed:
            await websocket.send_text(json.dumps({"type": "error", "reason": reason}))
            await websocket.close()
            return

        # Persist the user message
        try:
            save_message('user', prompt)
        except Exception:
            pass

        # Stream adapter chunks directly over the WebSocket
        async for chunk in model_adapter.stream_response(prompt):
            # chunk is a JSON string (e.g. {"type":"delta","text":"..."})
            await websocket.send_text(chunk)

        # After streaming completes, try to persist final message
        try:
            save_message('vinx', json.dumps({'streamed': True}))
        except Exception:
            pass

        await websocket.close()
    except WebSocketDisconnect:
        # Client disconnected
        return

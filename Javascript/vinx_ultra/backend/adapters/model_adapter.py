import os
import json
import asyncio
import requests
from typing import AsyncGenerator

# Adapter layer to select model provider based on environment variables.
# It provides two functions:
# - async generate_response(prompt) -> dict (type/text/table/image...)
# - async stream_response(prompt) -> AsyncGenerator[str] (yields JSON-encoded chunk strings)

ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_URL = os.getenv('ANTHROPIC_API_URL')
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_URL = os.getenv('OPENAI_API_URL')

# Simple fallback generator used when no provider keys are present.
def _fallback_response(prompt: str):
    if "table:" in prompt.lower():
        table = {
            "headers": ["Feature", "VINX ULTRA", "Competitor"],
            "rows": [
                ["Streaming", "Yes (demo)", "Yes"],
                ["Image generation", "Yes (placeholder)", "Yes"],
                ["Live UX", "Blue/white design", "Varies"]
            ]
        }
        return {"type": "table", "table": table}

    if "generate image" in prompt.lower() or "image:" in prompt.lower():
        return {"type": "image", "url": "/static/placeholder_image.svg", "caption": "Placeholder image (replace with real API)"}

    return {"type": "text", "text": f"VINX ULTRA (demo) reply to: {prompt}\n\nProvide an API key to enable Claude Sonnet 7 or OpenAI for production responses."}


async def generate_response(prompt: str) -> dict:
    """Return a JSON-serializable dict with keys like {type: 'text'|'table'|'image', ...}.
    Checks for provider keys and uses them; otherwise returns fallback.
    """
    # Prefer Anthropic if key present
    if ANTHROPIC_KEY and ANTHROPIC_URL:
        # Make a single non-streaming request to Anthropic's completion endpoint.
        payload = {
            "model": "claude-sonnet-7",
            "prompt": prompt,
            "max_tokens_to_sample": 1000,
            "temperature": 0.2,
        }
        headers = {"x-api-key": ANTHROPIC_KEY, "Content-Type": "application/json"}
        try:
            resp = requests.post(ANTHROPIC_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Anthropic responses vary by API; try several common keys
            text = data.get('completion') or data.get('output') or data.get('text') or ''
            # some providers use choices/messages
            if not text and 'choices' in data:
                choices = data.get('choices') or []
                if choices:
                    text = choices[0].get('message', {}).get('content') or choices[0].get('text', '')
            return {"type": "text", "text": text}
        except Exception as e:
            return {"type": "text", "text": f"[Anthropic error] {e} -- falling back to demo response."}

    if OPENAI_KEY and OPENAI_URL:
        # Minimal OpenAI-compatible POST example. This uses the REST endpoint shape and
        # may need adjustment if you prefer the official SDK.
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 800}
        try:
            resp = requests.post(OPENAI_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # adapt to ChatCompletion format
            choices = data.get('choices') or []
            if choices:
                msg = choices[0].get('message', {})
                text = msg.get('content') or choices[0].get('text') or str(data)
            else:
                text = str(data)
            return {"type": "text", "text": text}
        except Exception as e:
            return {"type": "text", "text": f"[OpenAI error] {e} -- falling back to demo response."}

    # No provider configured: return fallback
    return _fallback_response(prompt)


async def stream_response(prompt: str) -> AsyncGenerator[str, None]:
    """Asynchronously yield SSE-style JSON string chunks. Uses provider streaming when available; otherwise simulates streaming."""
    # Current approach: request a full response from the configured provider, then
    # stream it to the client in small chunks. This avoids fragile SSE parsing for
    # provider-specific streaming protocols while still providing a live UX.
    resp = await generate_response(prompt)
    if resp.get('type') == 'text':
        text = resp.get('text', '')
        # yield token-like chunks for a live typing effect
        for i in range(0, len(text), 48):
            chunk = text[i:i+48]
            yield json.dumps({"type": "delta", "text": chunk})
            await asyncio.sleep(0.05)
        yield json.dumps({"type": "done"})
    else:
        # Non-text - send single payload
        yield json.dumps({"type": resp.get('type'), "payload": resp})
        yield json.dumps({"type": "done"})

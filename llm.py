"""LLM client — uses Hermes runtime provider resolution.

Resolves the LLM endpoint from Hermes config (same as playlist_summarizer.py).
Auto-detects the Hermes installation path.

Usage:
    from llm import complete
    response = complete("Translate this to English: ...")
"""

from __future__ import annotations

import sys
from typing import Optional

# Resolve Hermes installation path
_HERMES_PATH = None
for candidate in ['/opt/hermes', '/home/hermes/.hermes/hermes']:
    if __import__('pathlib').Path(candidate).exists():
        _HERMES_PATH = candidate
        break

if _HERMES_PATH and _HERMES_PATH not in sys.path:
    sys.path.insert(0, _HERMES_PATH)

from hermes_cli.config import load_config  # type: ignore
from hermes_cli.runtime_provider import resolve_runtime_provider  # type: ignore
from openai import OpenAI  # type: ignore


def _get_client() -> tuple[OpenAI, str]:
    """Create an OpenAI-compatible client from Hermes config."""
    cfg = load_config()
    model_cfg = cfg.get('model', {}) if isinstance(cfg.get('model'), dict) else {}
    provider = model_cfg.get('provider') or 'auto'
    model = model_cfg.get('default') or ''
    runtime = resolve_runtime_provider(
        requested=provider,
        target_model='local/qwen3.5-9b',  # faster model for news pipeline
        explicit_api_key=model_cfg.get('api_key'),
        explicit_base_url=model_cfg.get('base_url'),
    )
    base_url = (runtime.get('base_url') or '').rstrip('/')
    api_key = runtime.get('api_key') or ''
    if not base_url or not api_key or not model:
        raise RuntimeError(
            'Resolved runtime provider is missing base_url, api_key, or model. '
            'Check Hermes config.yaml model section.'
        )
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=300)
    return client, 'local/qwen3.5-9b'


def complete(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Single LLM completion.

    Args:
        prompt: User prompt text.
        system: Optional system message (prepended to prompt).
        temperature: Sampling temperature.
        max_tokens: Max output tokens.

    Returns:
        LLM response text.
    """
    client, model = _get_client()

    # Embed system prompt in the input (Responses API doesn't use messages)
    if system:
        full_prompt = f"{system}\n\n{prompt}"
    else:
        full_prompt = prompt

    response = client.responses.create(
        model=model,
        input=full_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    text = (getattr(response, 'output_text', None) or '').strip()
    if not text:
        raise RuntimeError('Model returned an empty response')
    return text
"""Black-box target client (ADR-0004: OpenAI-compatible chat completions)."""

from __future__ import annotations

import asyncio
import os
import random
import time
from dataclasses import dataclass

import aiohttp


@dataclass
class TargetResult:
    text: str
    latency_ms: float
    error: str | None = None


class OpenAICompatTarget:
    """Talks to any deployed system exposing an OpenAI-compatible
    `POST {base_url}/chat/completions` endpoint. The system message is sent
    verbatim so suites control the operating preset; the target's own RAG /
    guardrail wrapper is expected to compose with it (that composition is
    exactly what Provar audits)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        timeout_s: float = 60.0,
        max_retries: int = 2,
        retry_backoff_s: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s

    async def complete(self, system: str, user: str) -> TargetResult:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout_s)
        last_err = None
        for attempt in range(self.max_retries + 1):
            t0 = time.monotonic()
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload, headers=headers) as resp:
                        body = await resp.text()
                        latency = (time.monotonic() - t0) * 1000.0
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            text = (
                                data.get("choices", [{}])[0]
                                .get("message", {})
                                .get("content", "")
                            )
                            return TargetResult(text=text or "", latency_ms=latency)
                        last_err = f"HTTP {resp.status}: {body[:200]}"
                        # Rate-limit aware exponential backoff (429 direct or
                        # wrapped inside a gateway 500 body).
                        if resp.status == 429 or "status 429" in body or "429" in body[:120]:
                            if attempt < self.max_retries:
                                await asyncio.sleep(
                                    self.retry_backoff_s * (2**attempt) + random.uniform(0.0, 1.0)
                                )
                                continue
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_err = f"{type(exc).__name__}: {exc}"
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_backoff_s * (attempt + 1))
        return TargetResult(text="", latency_ms=(time.monotonic() - t0) * 1000.0, error=last_err)


class EchoTarget:
    """Deterministic test fixture: echoes back a fixed reply. Used by the test
    suite — never by real evidence packs (labeled in run metadata)."""

    def __init__(self, reply: str = "NOT_COVERED: echo fixture has no KB [KB-00]"):
        self.reply = reply
        self.model = "echo-fixture"

    async def complete(self, system: str, user: str) -> TargetResult:
        return TargetResult(text=self.reply, latency_ms=0.0)


def target_from_config(cfg: dict) -> OpenAICompatTarget:
    kind = cfg.get("kind", "openai_compat")
    if kind != "openai_compat":
        raise ValueError(f"Unsupported target kind '{kind}' (only openai_compat in v0.1)")
    key = None
    env_name = cfg.get("api_key_env")
    if env_name:
        key = os.environ.get(env_name)
        if not key:
            raise ValueError(f"Environment variable {env_name} for target auth is not set")
    return OpenAICompatTarget(
        base_url=cfg["base_url"],
        model=cfg.get("model", "unknown"),
        api_key=key,
        temperature=float(cfg.get("temperature", 0.0)),
        timeout_s=float(cfg.get("timeout_s", 60.0)),
        max_retries=int(cfg.get("max_retries", 2)),
    )

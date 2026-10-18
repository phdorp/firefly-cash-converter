from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class LLMInterface:
    """Minimal client for an OpenAI-compatible chat completions endpoint.

    Intended for a local llama-server that exposes the OpenAI API (see
    ``LLAMA-LOCAL.md``). The client is deliberately thin: it sends chat
    messages, optionally constrains the reply to a JSON schema, and returns
    the assistant message content as text.

    Attributes:
        _base_url (str): Base URL of the server including the ``/v1`` suffix.
        _model (str): Model identifier served by the backend.
        _timeout_s (int): Per-request timeout in seconds.
        _session (requests.Session): Persistent HTTP session with auth headers.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "sk-noauth",
        timeout_s: int = 120,
    ) -> None:
        """Initialize the LLM client.

        Args:
            base_url (str): Base URL of the OpenAI-compatible server
                (e.g. "http://127.0.0.1:1234/v1").
            model (str): Model identifier to send in each request.
            api_key (str): Bearer token. The local server ignores it, so a
                placeholder is used by default.
            timeout_s (int): Per-request timeout in seconds. Defaults to 120.
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.0,
    ) -> str:
        """Send chat messages and return the assistant's message content.

        Args:
            messages (List[Dict[str, Any]]): Chat messages in OpenAI format.
            response_schema (Optional[Dict[str, Any]]): When provided, the reply
                is constrained to this JSON schema. Defaults to None.
            temperature (float): Sampling temperature. Defaults to 0.0 for
                deterministic output.

        Returns:
            str: The assistant message content.

        Raises:
            requests.HTTPError: If the HTTP request fails.
            KeyError: If the response does not contain assistant content.
        """
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": response_schema},
            }

        url = f"{self._base_url}/chat/completions"
        logger.debug(f"Sending chat request with {len(messages)} message(s)")
        response = self._session.post(url, json=payload, timeout=self._timeout_s)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

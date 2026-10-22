"""Provider-neutral LLM execution for architecture modeling bundles."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .cards import CardValidationError, validate_card
from .modeling import render_modeling_prompt

MAX_RESPONSE_BYTES = 2_000_000


class LLMModelError(RuntimeError):
    """Raised when an LLM response cannot become a valid draft card."""


@dataclass(frozen=True)
class OpenAICompatibleClient:
    """Small standard-library client for Chat Completions-compatible APIs."""

    base_url: str
    api_key: str
    model: str
    timeout: float = 120.0

    @property
    def endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only the requested JSON object. Do not include "
                        "Markdown fences or commentary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            detail = error.read(4_096).decode("utf-8", errors="replace")
            raise LLMModelError(
                f"model API returned HTTP {error.code}: {detail[:500]}"
            ) from error
        except URLError as error:
            raise LLMModelError(f"model API request failed: {error.reason}") from error
        except TimeoutError as error:
            raise LLMModelError("model API request timed out") from error

        if len(body) > MAX_RESPONSE_BYTES:
            raise LLMModelError("model API response exceeds the 2 MB limit")
        try:
            response_data = json.loads(body)
        except json.JSONDecodeError as error:
            raise LLMModelError("model API returned invalid JSON") from error
        return _extract_completion_content(response_data)


def model_bundles(
    bundle_dir: Path,
    output_dir: Path,
    client: OpenAICompatibleClient,
    system_ids: set[str] | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Model selected bundles and write only validated draft cards."""

    _check_output_dir(output_dir)

    bundle_paths = (
        [bundle_dir] if bundle_dir.is_file() else sorted(bundle_dir.glob("*.json"))
    )
    if system_ids:
        bundle_paths = [path for path in bundle_paths if path.stem in system_ids]
    if not bundle_paths:
        raise LLMModelError(f"no modeling bundles found in {bundle_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for bundle_path in bundle_paths:
        bundle = _load_json_object(bundle_path)
        card = model_bundle(bundle, client)
        output_path = output_dir / f"{card['id']}.json"
        if output_path.exists() and not overwrite:
            raise LLMModelError(
                f"{output_path}: refusing to overwrite existing draft; use --force"
            )
        output_path.write_text(
            json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        written.append(output_path)
    return written


def model_bundle(
    bundle: dict[str, Any], client: OpenAICompatibleClient
) -> dict[str, Any]:
    """Run one bundle, enforce evidence boundaries, and validate its card."""

    system = bundle.get("system")
    if not isinstance(system, dict) or not system.get("id"):
        raise LLMModelError("modeling bundle has no valid system metadata")
    existing_draft = bundle.get("existing_structural_draft")
    if not isinstance(existing_draft, dict):
        raise LLMModelError("modeling bundle has no existing draft")
    existing_evidence = {
        item.get("id"): item
        for item in existing_draft.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if not existing_evidence:
        raise LLMModelError("modeling bundle has no usable evidence records")
    response_text = client.complete(render_modeling_prompt(bundle))
    card = extract_card_json(response_text)
    if card.get("id") != system["id"]:
        raise LLMModelError(
            f"model returned id {card.get('id')!r}; expected {system['id']!r}"
        )
    used_evidence = _card_evidence_ids(card)
    unknown = used_evidence - existing_evidence.keys()
    if unknown:
        raise LLMModelError(
            f"model cited evidence not present in the bundle: {sorted(unknown)}"
        )
    returned_evidence = card.get("evidence")
    if not isinstance(returned_evidence, list) or not returned_evidence:
        raise LLMModelError("model returned no evidence records")
    for evidence in returned_evidence:
        if not isinstance(evidence, dict) or not isinstance(evidence.get("id"), str):
            raise LLMModelError("model returned an invalid evidence record")
        evidence_id = evidence["id"]
        if evidence_id not in existing_evidence:
            raise LLMModelError(
                f"model returned evidence not present in the bundle: {evidence_id}"
            )
        if evidence != existing_evidence[evidence_id]:
            raise LLMModelError(
                f"model changed evidence record from the bundle: {evidence_id}"
            )
    card.setdefault("version_context", f"commit {system['commit']}")
    try:
        validate_card(card)
    except (CardValidationError, TypeError, AttributeError) as error:
        raise LLMModelError(
            f"model returned an invalid Architecture Card: {error}"
        ) from error
    return card


def extract_card_json(response_text: str) -> dict[str, Any]:
    """Extract one JSON object from plain, fenced, or wrapped model output."""

    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise LLMModelError("model response did not contain a JSON object")


def client_from_environment(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = 120.0,
) -> OpenAICompatibleClient:
    """Construct a client from explicit values or standard environment variables."""

    resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved_key:
        raise LLMModelError("missing API key; pass --api-key or set OPENAI_API_KEY")
    resolved_model = model or os.environ.get("MATHEN_LLM_MODEL")
    if not resolved_model:
        raise LLMModelError("missing model; pass --model or set MATHEN_LLM_MODEL")
    return OpenAICompatibleClient(
        base_url=base_url
        or os.environ.get("MATHEN_LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=resolved_key,
        model=resolved_model,
        timeout=timeout,
    )


def _extract_completion_content(response_data: Any) -> str:
    try:
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise LLMModelError(
            "model API response has no chat completion content"
        ) from error
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        if parts:
            return "".join(parts)
    raise LLMModelError("model API returned unsupported message content")


def _card_evidence_ids(card: dict[str, Any]) -> set[str]:
    references: set[str] = set()
    features = card.get("features", [])
    for feature in features if isinstance(features, list) else []:
        if isinstance(feature, dict):
            evidence_ids = feature.get("evidence_ids", [])
            if isinstance(evidence_ids, list):
                references.update(
                    evidence_id
                    for evidence_id in evidence_ids
                    if isinstance(evidence_id, str)
                )
    views = card.get("mathematical_views", [])
    for view in views if isinstance(views, list) else []:
        if isinstance(view, dict):
            evidence_ids = view.get("evidence_ids", [])
            if isinstance(evidence_ids, list):
                references.update(
                    evidence_id
                    for evidence_id in evidence_ids
                    if isinstance(evidence_id, str)
                )
    return references


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LLMModelError(f"{path}: cannot load bundle: {error}") from error
    if not isinstance(data, dict):
        raise LLMModelError(f"{path}: bundle must be a JSON object")
    return data


def _check_output_dir(output_dir: Path) -> None:
    """Reject output locations that could overwrite reviewed canonical cards."""

    try:
        resolved = output_dir.resolve()
    except OSError as error:
        raise LLMModelError(
            f"cannot resolve model output directory: {error}"
        ) from error
    systems_dirs = [
        parent for parent in (resolved, *resolved.parents) if parent.name == "systems"
    ]
    if systems_dirs:
        raise LLMModelError(
            "model output must stay in a draft directory; data/systems is protected"
        )

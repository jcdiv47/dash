"""Model provider configuration for Dash."""

import json
from os import getenv
from typing import Any

from agno.models.openrouter import OpenRouterResponses

OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_BASE_URL = getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL_ID = getenv("OPENROUTER_MODEL_ID", "openai/gpt-5.4")
OPENROUTER_EMBEDDING_MODEL_ID = getenv("OPENROUTER_EMBEDDING_MODEL_ID", "openai/text-embedding-3-small")
OPENROUTER_EMBEDDING_DIMENSIONS = int(getenv("OPENROUTER_EMBEDDING_DIMENSIONS", "1536"))

_OPENROUTER_PROVIDER_LIST_ENVS = {
    "order": "OPENROUTER_PROVIDER_ORDER",
    "only": "OPENROUTER_PROVIDER_ONLY",
    "ignore": "OPENROUTER_PROVIDER_IGNORE",
    "quantizations": "OPENROUTER_PROVIDER_QUANTIZATIONS",
}
_OPENROUTER_PROVIDER_BOOL_ENVS = {
    "allow_fallbacks": "OPENROUTER_PROVIDER_ALLOW_FALLBACKS",
    "require_parameters": "OPENROUTER_PROVIDER_REQUIRE_PARAMETERS",
    "zdr": "OPENROUTER_PROVIDER_ZDR",
    "enforce_distillable_text": "OPENROUTER_PROVIDER_ENFORCE_DISTILLABLE_TEXT",
}
_OPENROUTER_SORT_VALUES = {"price", "throughput", "latency"}
_OPENROUTER_SORT_PARTITIONS = {"model", "none"}


def get_openrouter_api_key(*, required: bool = False) -> str | None:
    """Return the OpenRouter API key without falling back to OPENAI_API_KEY."""
    api_key = getenv(OPENROUTER_API_KEY_ENV)
    if required and not api_key:
        raise RuntimeError(f"{OPENROUTER_API_KEY_ENV} is required for OpenRouter model calls.")
    return api_key


def openrouter_default_headers() -> dict[str, str] | None:
    """Optional OpenRouter attribution headers."""
    headers: dict[str, str] = {}
    http_referer = getenv("OPENROUTER_HTTP_REFERER")
    app_title = getenv("OPENROUTER_APP_TITLE")

    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if app_title:
        headers["X-OpenRouter-Title"] = app_title

    return headers or None


def _get_env(name: str) -> str | None:
    value = getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_csv_env(name: str) -> list[str] | None:
    value = _get_env(name)
    if value is None:
        return None
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or None


def _parse_bool_env(name: str) -> bool | None:
    value = _get_env(name)
    if value is None:
        return None

    normalized = value.lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False

    raise RuntimeError(f"{name} must be a boolean: true/false, yes/no, on/off, or 1/0.")


def _parse_json_object_env(name: str) -> dict[str, Any] | None:
    value = _get_env(name)
    if value is None:
        return None

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON: {exc.msg}.") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"{name} must be a JSON object.")
    if not all(isinstance(key, str) for key in parsed):
        raise RuntimeError(f"{name} must use string keys.")

    return parsed


def _parse_json_value_env(name: str) -> Any:
    value = _get_env(name)
    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON: {exc.msg}.") from exc


def _parse_sort_env(name: str) -> str | dict[str, Any] | None:
    value = _get_env(name)
    if value is None:
        return None

    if value.startswith("{"):
        parsed = _parse_json_value_env(name)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"{name} must be a string or JSON object.")

        sort_by = parsed.get("by")
        if sort_by is not None and sort_by not in _OPENROUTER_SORT_VALUES:
            raise RuntimeError(f"{name}.by must be one of: {', '.join(sorted(_OPENROUTER_SORT_VALUES))}.")

        partition = parsed.get("partition")
        if partition is not None and partition not in _OPENROUTER_SORT_PARTITIONS:
            raise RuntimeError(f"{name}.partition must be one of: {', '.join(sorted(_OPENROUTER_SORT_PARTITIONS))}.")

        return parsed

    if value not in _OPENROUTER_SORT_VALUES:
        raise RuntimeError(f"{name} must be one of: {', '.join(sorted(_OPENROUTER_SORT_VALUES))}.")
    return value


def _parse_number_or_object_env(name: str) -> int | float | dict[str, Any] | None:
    parsed = _parse_json_value_env(name)
    if parsed is None:
        return None

    if isinstance(parsed, bool) or not isinstance(parsed, (int, float, dict)):
        raise RuntimeError(f"{name} must be a number or JSON object.")
    if isinstance(parsed, dict) and not all(isinstance(key, str) for key in parsed):
        raise RuntimeError(f"{name} must use string keys.")

    return parsed


def _openrouter_provider_from_env() -> dict[str, Any]:
    provider = _parse_json_object_env("OPENROUTER_PROVIDER_JSON") or {}

    for field, env_name in _OPENROUTER_PROVIDER_LIST_ENVS.items():
        values = _parse_csv_env(env_name)
        if values is not None:
            provider[field] = values

    for field, env_name in _OPENROUTER_PROVIDER_BOOL_ENVS.items():
        value = _parse_bool_env(env_name)
        if value is not None:
            provider[field] = value

    data_collection = _get_env("OPENROUTER_PROVIDER_DATA_COLLECTION")
    if data_collection is not None:
        if data_collection not in {"allow", "deny"}:
            raise RuntimeError("OPENROUTER_PROVIDER_DATA_COLLECTION must be either 'allow' or 'deny'.")
        provider["data_collection"] = data_collection

    sort = _parse_sort_env("OPENROUTER_PROVIDER_SORT")
    if sort is not None:
        provider["sort"] = sort

    preferred_min_throughput = _parse_number_or_object_env("OPENROUTER_PROVIDER_PREFERRED_MIN_THROUGHPUT")
    if preferred_min_throughput is not None:
        provider["preferred_min_throughput"] = preferred_min_throughput

    preferred_max_latency = _parse_number_or_object_env("OPENROUTER_PROVIDER_PREFERRED_MAX_LATENCY")
    if preferred_max_latency is not None:
        provider["preferred_max_latency"] = preferred_max_latency

    max_price = _parse_json_object_env("OPENROUTER_PROVIDER_MAX_PRICE")
    if max_price is not None:
        provider["max_price"] = max_price

    return provider


def _openrouter_provider_for_model(model_id: str | None) -> dict[str, Any] | None:
    provider_by_model = _parse_json_object_env("OPENROUTER_PROVIDER_BY_MODEL_JSON")
    if not provider_by_model:
        return None

    selected = None
    if model_id is not None:
        selected = provider_by_model.get(model_id)
    if selected is None:
        selected = provider_by_model.get("default", provider_by_model.get("*"))
    if selected is None:
        return None
    if not isinstance(selected, dict):
        raise RuntimeError("OPENROUTER_PROVIDER_BY_MODEL_JSON values must be JSON objects.")
    if not all(isinstance(key, str) for key in selected):
        raise RuntimeError("OPENROUTER_PROVIDER_BY_MODEL_JSON provider objects must use string keys.")

    return selected


def openrouter_provider_preferences(model_id: str | None = OPENROUTER_MODEL_ID) -> dict[str, Any] | None:
    """Build OpenRouter provider routing preferences from environment variables."""
    provider = _openrouter_provider_from_env()
    model_provider = _openrouter_provider_for_model(model_id)
    if model_provider:
        provider.update(model_provider)

    return provider or None


def openrouter_fallback_model_ids() -> list[str] | None:
    """Return fallback model IDs for OpenRouter dynamic model routing."""
    return _parse_csv_env("OPENROUTER_FALLBACK_MODEL_IDS")


def openrouter_extra_body(
    *,
    model_id: str | None = OPENROUTER_MODEL_ID,
    include_fallback_models: bool = True,
) -> dict[str, Any] | None:
    """Return OpenRouter-only request body parameters."""
    extra_body: dict[str, Any] = {}

    provider = openrouter_provider_preferences(model_id)
    if provider:
        extra_body["provider"] = provider

    if include_fallback_models:
        fallback_model_ids = openrouter_fallback_model_ids()
        if fallback_model_ids:
            extra_body["models"] = fallback_model_ids

    return extra_body or None


def openrouter_client_kwargs(*, required_api_key: bool = False) -> dict[str, Any]:
    """Shared OpenAI-compatible client kwargs for OpenRouter."""
    kwargs: dict[str, Any] = {
        "base_url": OPENROUTER_BASE_URL,
    }

    api_key = get_openrouter_api_key(required=required_api_key)
    if api_key:
        kwargs["api_key"] = api_key

    default_headers = openrouter_default_headers()
    if default_headers:
        kwargs["default_headers"] = default_headers

    return kwargs


def openrouter_embedder_kwargs(*, required_api_key: bool = False) -> dict[str, Any]:
    """OpenAIEmbedder kwargs for OpenRouter."""
    kwargs: dict[str, Any] = {
        "base_url": OPENROUTER_BASE_URL,
    }

    api_key = get_openrouter_api_key(required=required_api_key)
    if api_key:
        kwargs["api_key"] = api_key

    default_headers = openrouter_default_headers()
    if default_headers:
        kwargs["client_params"] = {"default_headers": default_headers}

    return kwargs


def build_openrouter_model() -> OpenRouterResponses:
    """Create a fresh OpenRouter model instance for agents or eval judges."""
    return OpenRouterResponses(
        id=OPENROUTER_MODEL_ID,
        extra_body=openrouter_extra_body(model_id=OPENROUTER_MODEL_ID, include_fallback_models=False),
        models=openrouter_fallback_model_ids(),
        **openrouter_client_kwargs(),
    )

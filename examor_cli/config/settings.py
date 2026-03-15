"""Centralized configuration for Examor CLI."""

from __future__ import annotations

import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


def _get_env(name: str, default: str | None = None) -> str:
    """Helper to read environment variable with optional default."""
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


# ===================== Database configuration =====================
DATABASE_CONFIG = {
    "host": os.getenv("EXAMOR_DB_HOST", "localhost"),
    "port": int(os.getenv("EXAMOR_DB_PORT", "52020")),
    "user": os.getenv("EXAMOR_DB_USER", "root"),
    "password": os.getenv("EXAMOR_DB_PASSWORD", "123456"),
    "database": os.getenv("EXAMOR_DB_NAME", "examor"),
}


# ===================== LLM configuration =====================
LLM_CONFIG = {
    # API key is required, no hard-coded secret
    "api_key": _get_env("EXAMOR_LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY")),
    "base_url": os.getenv("EXAMOR_LLM_BASE_URL", "https://api.deepseek.com/v1"),
    "model": os.getenv("EXAMOR_LLM_MODEL", "deepseek-chat"),
    "temperature": float(os.getenv("EXAMOR_LLM_TEMPERATURE", "0.7")),
}


# ===================== Business configuration =====================
DEFAULT_QUESTION_NUM = int(os.getenv("EXAMOR_DEFAULT_QUESTION_NUM", "5"))

SUPPORTED_TYPES = ["single_choice", "short_answer", "fill_blank"]

TYPE_CN_MAP = {
    "single_choice": "单选题",
    "short_answer": "简答题",
    "fill_blank": "填空题",
}

# Default number of options for single choice questions
SINGLE_CHOICE_OPTION_NUM = int(os.getenv("EXAMOR_SINGLE_CHOICE_OPTION_NUM", "4"))


__all__ = [
    "DATABASE_CONFIG",
    "LLM_CONFIG",
    "DEFAULT_QUESTION_NUM",
    "SUPPORTED_TYPES",
    "TYPE_CN_MAP",
    "SINGLE_CHOICE_OPTION_NUM",
]


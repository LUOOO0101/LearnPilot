"""Configuration subpackage for Examor CLI."""

from .settings import (
    DATABASE_CONFIG,
    LLM_CONFIG,
    DEFAULT_QUESTION_NUM,
    SUPPORTED_TYPES,
    TYPE_CN_MAP,
    SINGLE_CHOICE_OPTION_NUM,
)

__all__ = [
    "DATABASE_CONFIG",
    "LLM_CONFIG",
    "DEFAULT_QUESTION_NUM",
    "SUPPORTED_TYPES",
    "TYPE_CN_MAP",
    "SINGLE_CHOICE_OPTION_NUM",
]


"""
Core Enums
==========
Centralized enum definitions that replace magic strings across the codebase.

All enums extend ``str, Enum`` so they serialize as plain strings and remain
backward compatible with existing string comparisons.
"""

from enum import Enum


class CircuitState(str, Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


class ProtectionType(str, Enum):
    CHALLENGE = 'challenge'
    BLOCKED = 'blocked'
    RATELIMITED = 'ratelimited'
    AKAMAI = 'akamai'
    DATADOME = 'datadome'
    PERIMETERX = 'perimeterx'
    INCAPSULA = 'incapsula'
    CAPTCHA = 'captcha'
    NONE = 'none'


class ProxyType(str, Enum):
    SINGLE = 'single'
    ROTATING = 'rotating'
    RESIDENTIAL = 'residential'
    SOCKS5 = 'socks5'


class RotationStrategy(str, Enum):
    ROUND_ROBIN = 'round_robin'
    RANDOM = 'random'
    SMART = 'smart'


class SelectorType(str, Enum):
    CSS = 'css'
    XPATH = 'xpath'
    JSON = 'json'


class Language(str, Enum):
    ENGLISH = 'English'
    BENGALI = 'Bengali'


class TaskStatus(str, Enum):
    SUCCESS = 'success'
    FAILED = 'failed'
    TIMEOUT = 'timeout'


class ExtractionSource(str, Enum):
    JSON_LD = 'json-ld'
    TRAFILATURA = 'trafilatura'
    HEURISTIC = 'heuristic'
    REGEX = 'regex'
    NONE = 'none'

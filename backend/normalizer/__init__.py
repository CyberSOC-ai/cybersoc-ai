"""Wazuh alert to incident v1 conversion (S1-T06)."""

from .wazuh import NormalizationError, normalize_alert

__all__ = ['NormalizationError', 'normalize_alert']

"""Degradation detection — compares arithmetic against human-declared thresholds (ZFC)."""

from arbiter.detection.detector import ThresholdDetector
from arbiter.detection.protocol import Alert, DegradationDetector

__all__ = ["Alert", "DegradationDetector", "ThresholdDetector"]

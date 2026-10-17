"""
One Euro Filter for real-time noise and tremor filtering with minimum latency.
Based on the CHI 2012 paper by Casiez, Roussel, and Vogel.
"""
import math
import time
from typing import Optional, Tuple


class OneEuroFilter:
    """
    First-order low-pass filter with an adaptive cutoff frequency.
    At low speed: low cutoff frequency filters out jitter and tremor completely.
    At high speed: cutoff frequency rises dynamically to reduce lag to near zero.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.015,
        d_cutoff: float = 1.0
    ):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev: Optional[float] = None
        self.dx_prev: float = 0.0
        self.t_prev: Optional[float] = None

    def reset(self):
        """Resets filter state when tracking is lost."""
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        if timestamp is None:
            timestamp = time.time()

        if self.x_prev is None or self.t_prev is None:
            self.x_prev = float(x)
            self.dx_prev = 0.0
            self.t_prev = timestamp
            return float(x)

        dt = timestamp - self.t_prev
        if dt <= 0.0001:
            dt = 0.001


        # Estimate rate of change (derivative)
        dx = (x - self.x_prev) / dt
        alpha_d = self._alpha(self.d_cutoff, dt)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # Dynamic cutoff frequency based on velocity
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        alpha = self._alpha(cutoff, dt)
        x_hat = alpha * x + (1.0 - alpha) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = timestamp
        return x_hat


class PointFilter2D:
    """Two-dimensional 1 Euro Filter for stabilizing 2D (x, y) coordinates."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.015,
        d_cutoff: float = 1.0
    ):
        self.filter_x = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self.filter_y = OneEuroFilter(min_cutoff, beta, d_cutoff)

    def reset(self):
        """Resets both X and Y filters."""
        self.filter_x.reset()
        self.filter_y.reset()

    def filter(
        self,
        x: float,
        y: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float]:
        if timestamp is None:
            timestamp = time.time()
        fx = self.filter_x.filter(x, timestamp)
        fy = self.filter_y.filter(y, timestamp)
        return fx, fy

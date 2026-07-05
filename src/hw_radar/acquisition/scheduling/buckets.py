"""Two-level token buckets (per-source + per-domain), C.2.

Pure and clock-injected: callers pass `now_s` from a monotonic-ish clock; the
poller uses `time.monotonic()`. Serializable for the ERR-007 checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

DOMAIN_RATE_PER_MIN = 30.0  # politeness default per domain; OQ9-provisional
DOMAIN_BURST = 10


@dataclass
class TokenBucket:
    capacity: float
    refill_per_s: float
    tokens: float
    updated_at: float

    def refill(self, now_s: float) -> None:
        elapsed = max(0.0, now_s - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
        self.updated_at = now_s

    def can_acquire(self, now_s: float, cost: float = 1.0) -> bool:
        self.refill(now_s)
        return self.tokens >= cost

    def acquire(self, now_s: float, cost: float = 1.0) -> bool:
        if not self.can_acquire(now_s, cost):
            return False
        self.tokens -= cost
        return True


def _bucket(rate_per_min: float, burst: int, now_s: float) -> TokenBucket:
    return TokenBucket(
        capacity=float(burst),
        refill_per_s=rate_per_min / 60.0,
        tokens=float(burst),
        updated_at=now_s,
    )


@dataclass
class BucketRegistry:
    source_buckets: dict[str, TokenBucket] = field(default_factory=dict)
    domain_buckets: dict[str, TokenBucket] = field(default_factory=dict)

    def configure_source(self, key: str, *, rate_per_min: float, burst: int, now_s: float) -> None:
        self.source_buckets[key] = _bucket(rate_per_min, burst, now_s)

    def configure_domain(
        self, domain: str, *, rate_per_min: float, burst: int, now_s: float
    ) -> None:
        self.domain_buckets[domain] = _bucket(rate_per_min, burst, now_s)

    def _domain(self, domain: str, now_s: float) -> TokenBucket:
        if domain not in self.domain_buckets:
            self.configure_domain(
                domain, rate_per_min=DOMAIN_RATE_PER_MIN, burst=DOMAIN_BURST, now_s=now_s
            )
        return self.domain_buckets[domain]

    def admit(self, source_key: str, domain: str, now_s: float) -> bool:
        """Both-or-neither: a denial must not burn tokens at the other level."""
        source = self.source_buckets.get(source_key)
        if source is None:
            return False
        domain_bucket = self._domain(domain, now_s)
        if not (source.can_acquire(now_s) and domain_bucket.can_acquire(now_s)):
            return False
        source.acquire(now_s)
        domain_bucket.acquire(now_s)
        return True

    def to_state(self) -> dict[str, object]:
        def dump(buckets: dict[str, TokenBucket]) -> dict[str, dict[str, float]]:
            return {
                key: {
                    "capacity": b.capacity,
                    "refill_per_s": b.refill_per_s,
                    "tokens": b.tokens,
                    "updated_at": b.updated_at,
                }
                for key, b in buckets.items()
            }

        return {"sources": dump(self.source_buckets), "domains": dump(self.domain_buckets)}

    @classmethod
    def from_state(cls, state: dict[str, object]) -> BucketRegistry:
        def load(raw: object) -> dict[str, TokenBucket]:
            out: dict[str, TokenBucket] = {}
            for key, values in cast("dict[str, dict[str, float]]", raw).items():
                out[key] = TokenBucket(**values)
            return out

        return cls(
            source_buckets=load(state.get("sources", {})),
            domain_buckets=load(state.get("domains", {})),
        )

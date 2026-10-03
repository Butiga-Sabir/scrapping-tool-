"""
Combination generator module
Builds accumulators that reach the payout target with the HIGHEST combined win probability.
"""
import itertools
import logging
from math import prod

from config import Config

logger = logging.getLogger(__name__)


class CombinationGenerator:
    """Generates betting combinations ranked by probability of winning"""

    def __init__(self, max_matches, max_combinations):
        self.max_matches = min(max_matches, Config.MAX_LEGS)
        self.max_combinations = max_combinations
        self.meets_payout = True   # False when only a best-effort slip was possible

    # ------------------------------------------------------------- metrics
    @staticmethod
    def combined_odds(combo):
        return prod(s['odds'] for s in combo)

    @staticmethod
    def combined_probability(combo):
        """Product of leg probabilities (legs are treated as independent)."""
        return prod((s.get('win_prob') or 0.0) for s in combo)

    # ---------------------------------------------------------- generation
    def _build_pool(self, selections):
        """Most likely selections first; cap pool size to keep the search bounded."""
        ranked = sorted(selections, key=lambda s: s.get('win_prob') or 0.0, reverse=True)
        return ranked[:Config.POOL_SIZE]

    def generate_combinations(self, selections, min_payout, stake):
        pool = self._build_pool(selections)
        target_odds = min_payout / stake
        max_size = min(self.max_matches, len(pool))
        logger.info(f"Pool: {len(pool)} selections | target odds >= {target_odds:.2f} | max legs {max_size}")

        self.meets_payout = True
        found, first_size = [], None

        for size in range(1, max_size + 1):
            for combo in itertools.combinations(pool, size):
                if not self._is_valid_combination(combo):
                    continue
                if self.combined_odds(combo) >= target_odds:
                    found.append(list(combo))
            if found and first_size is None:
                first_size = size
            # look one size beyond the first hit (different mixes can beat it), then stop
            if first_size is not None and size >= first_size + 1:
                break

        if found:
            found.sort(key=self.combined_probability, reverse=True)
            return found[:self.max_combinations]

        # Payout target unreachable with the allowed legs: return the best-effort slip
        self.meets_payout = False
        logger.warning("No combination reaches the payout target; returning best effort")
        best = self._best_effort(pool, max_size)
        return [best] if best else []

    def _best_effort(self, pool, max_size):
        chosen, used = [], set()
        for sel in sorted(pool, key=lambda s: s['odds'], reverse=True):
            key = (sel['home_team'], sel['away_team'])
            if key in used:
                continue
            used.add(key)
            chosen.append(sel)
            if len(chosen) == max_size:
                break
        return chosen

    def _is_valid_combination(self, combination):
        """One selection per fixture."""
        keys = [(s['home_team'], s['away_team']) for s in combination]
        return len(keys) == len(set(keys))

    # ------------------------------------------------------------- sorting
    def sort_combinations_by_probability(self, combinations):
        return sorted(combinations, key=self.combined_probability, reverse=True)

    def sort_combinations_by_odds(self, combinations):
        return sorted(combinations, key=self.combined_odds, reverse=True)

    def sort_combinations_by_payout(self, combinations, stake):
        return sorted(combinations, key=lambda c: self.combined_odds(c) * stake, reverse=True)

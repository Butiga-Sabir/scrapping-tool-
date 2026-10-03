"""
Selection and filtering module
Filters fixtures based on user criteria and calculates confidence indicators
"""
import logging
from config import Config

logger = logging.getLogger(__name__)

class SelectionFilter:
    """Filters fixtures based on user criteria"""
    
    def __init__(self, min_odds, max_odds, min_payout, stake, market_type,
                 exclude_draws=False, min_win_prob=None):
        self.min_win_prob = Config.DEFAULT_MIN_WIN_PROB if min_win_prob is None else min_win_prob
        self.min_odds = min_odds
        self.max_odds = max_odds
        self.min_payout = min_payout
        self.stake = stake
        self.market_type = market_type
        self.exclude_draws = exclude_draws
    
    def filter_fixtures(self, fixtures):
        """Filter fixtures based on criteria"""
        logger.info(f"Filtering {len(fixtures)} fixtures")
        
        filtered_selections = []
        
        for fixture in fixtures:
            # Check each possible selection
            selections = self._get_selections_for_fixture(fixture)
            self._attach_probabilities(fixture, selections)
            
            for selection in selections:
                if self._meets_criteria(selection):
                    selection['confidence'] = self._calculate_confidence(selection)
                    selection['reason'] = self._get_selection_reason(selection)
                    # Ensure market_type is set for Selenium navigation
                    if 'market_type' not in selection:
                        selection['market_type'] = '1X2'  # Default
                    filtered_selections.append(selection)
        
        logger.info(f"Found {len(filtered_selections)} qualifying selections")
        return filtered_selections
    
    def best_selection(self, fixture):
        """Streaming mode: return the single best clickable pick for one fixture
        (Home/Away Win only - double chance odds are calculated, not shown on the
        1X2 page), or None if nothing meets the odds range and probability floor."""
        if self.market_type == Config.MARKET_DOUBLE_CHANCE:
            return None   # Double Chance mode never uses Home/Away Win
        selections = self._get_selections_for_fixture(fixture)
        self._attach_probabilities(fixture, selections)
        ok = [s for s in selections
              if s['selection'] in (Config.SELECTION_HOME_WIN, Config.SELECTION_AWAY_WIN)
              and self._meets_criteria(s)]
        if not ok:
            return None
        best = max(ok, key=lambda s: s['win_prob'])
        best['confidence'] = self._calculate_confidence(best)
        best['reason'] = self._get_selection_reason(best)
        return best

    @staticmethod
    def dc_row_is_valid(fixture):
        """True only if the three prices really look like Double Chance (1X / 12 / X2).
        Each DC outcome covers two results, so sum(1/odds) is ~2 (+margin). A 1X2 row
        sums to ~1.05-1.15 - if we see that, we are reading win prices and must not use them."""
        o1x, o12, ox2 = fixture.get('dc_1x'), fixture.get('dc_12'), fixture.get('dc_x2')
        if not (o1x and o12 and ox2):
            return False
        return 1.6 <= (1.0 / o1x + 1.0 / o12 + 1.0 / ox2) <= 2.7

    def best_dc_selection(self, fixture):
        """Streaming mode on the Double Chance page: fixture carries the REAL 1X / X2 / 12
        prices. Returns the better of 1X and X2 (12 is never used; page column order is 1X, X2, 12) that meets the odds range
        and probability floor, or None.

        Probability: the three DC outcomes each cover two results, so their implied
        probabilities sum to 2 (plus margin). Normalising to 2 removes the margin."""
        if not self.dc_row_is_valid(fixture):
            return None
        o1x, o12, ox2 = fixture['dc_1x'], fixture['dc_12'], fixture['dc_x2']
        raw = {'1X': 1.0 / o1x, '12': 1.0 / o12, 'X2': 1.0 / ox2}
        total = sum(raw.values())
        margin = total / 2.0 - 1.0
        candidates = []
        for name, odds in (('1X', o1x), ('X2', ox2)):   # 12 is never a candidate
            sel = {
                'competition': fixture['competition'], 'date_time': fixture['date_time'],
                'home_team': fixture['home_team'], 'away_team': fixture['away_team'],
                'market': Config.MARKET_DOUBLE_CHANCE, 'market_type': name,
                'selection': name, 'odds': odds, 'payout': odds * self.stake,
                'win_prob': 2.0 * raw[name] / total, 'margin': margin, 'derived': False,
                'col_index': (fixture.get('dc_positions') or {'1x': 0, 'x2': 1, '12': 2})[name.lower()],
            }
            if self._meets_criteria(sel):
                candidates.append(sel)
        if not candidates:
            return None
        best = max(candidates, key=lambda c: c['win_prob'])
        best['confidence'] = self._calculate_confidence(best)
        best['reason'] = self._get_selection_reason(best)
        return best

    def _get_selections_for_fixture(self, fixture):
        """Get all possible selections for a fixture"""
        selections = []
        
        # WIN market selections (NO DRAWS - as per user preference)
        if self.market_type in [Config.MARKET_WIN, Config.MARKET_MIXED]:
            if fixture['home_odds']:
                selections.append({
                    'competition': fixture['competition'],
                    'date_time': fixture['date_time'],
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'market': Config.MARKET_WIN,
                    'market_type': '1X2',
                    'selection': Config.SELECTION_HOME_WIN,
                    'odds': fixture['home_odds'],
                    'payout': fixture['home_odds'] * self.stake
                })
            
            # DRAWS REMOVED - as per user preference for no single draws
            # if not self.exclude_draws and fixture['draw_odds']:
            #     selections.append({
            #         'competition': fixture['competition'],
            #         'date_time': fixture['date_time'],
            #         'home_team': fixture['home_team'],
            #         'away_team': fixture['away_team'],
            #         'market': Config.MARKET_WIN,
            #         'market_type': '1X2',
            #         'selection': Config.SELECTION_DRAW,
            #         'odds': fixture['draw_odds'],
            #         'payout': fixture['draw_odds'] * self.stake
            #     })
            
            if fixture['away_odds']:
                selections.append({
                    'competition': fixture['competition'],
                    'date_time': fixture['date_time'],
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'market': Config.MARKET_WIN,
                    'market_type': '1X2',
                    'selection': Config.SELECTION_AWAY_WIN,
                    'odds': fixture['away_odds'],
                    'payout': fixture['away_odds'] * self.stake
                })
        
        # DOUBLE CHANCE market selections (NO 12 - as per user preference)
        if self.market_type in [Config.MARKET_DOUBLE_CHANCE, Config.MARKET_MIXED]:
            # Calculate double chance odds
            if fixture['home_odds'] and fixture['draw_odds']:
                odds_1x = self._calculate_double_chance_odds(fixture['home_odds'], fixture['draw_odds'])
                selections.append({
                    'competition': fixture['competition'],
                    'date_time': fixture['date_time'],
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'market': Config.MARKET_DOUBLE_CHANCE,
                    'market_type': '1X',
                    'selection': Config.SELECTION_1X,
                    'odds': odds_1x,
                    'payout': odds_1x * self.stake
                })
            
            if fixture['draw_odds'] and fixture['away_odds']:
                odds_x2 = self._calculate_double_chance_odds(fixture['draw_odds'], fixture['away_odds'])
                selections.append({
                    'competition': fixture['competition'],
                    'date_time': fixture['date_time'],
                    'home_team': fixture['home_team'],
                    'away_team': fixture['away_team'],
                    'market': Config.MARKET_DOUBLE_CHANCE,
                    'market_type': 'X2',
                    'selection': Config.SELECTION_X2,
                    'odds': odds_x2,
                    'payout': odds_x2 * self.stake
                })
            
            # 12 REMOVED - as per user preference for no 12 separate
            # if fixture['home_odds'] and fixture['away_odds']:
            #     odds_12 = self._calculate_double_chance_odds(fixture['home_odds'], fixture['away_odds'])
            #     selections.append({
            #         'competition': fixture['competition'],
            #         'date_time': fixture['date_time'],
            #         'home_team': fixture['home_team'],
            #         'away_team': fixture['away_team'],
            #         'market': Config.MARKET_DOUBLE_CHANCE,
            #         'market_type': '12',
            #         'selection': Config.SELECTION_12,
            #         'odds': odds_12,
            #         'payout': odds_12 * self.stake
            #     })
        
        return selections
    
    @staticmethod
    def implied_probabilities(fixture):
        """Market-implied probabilities with the bookmaker margin removed.
        Returns dict {'home','draw','away','margin'} (draw may be None for 2-way input)."""
        h, d, a = fixture.get('home_odds'), fixture.get('draw_odds'), fixture.get('away_odds')
        raw = {k: (1.0 / v) for k, v in (('home', h), ('draw', d), ('away', a)) if v}
        total = sum(raw.values())
        if total <= 0 or len(raw) < 2:
            return None
        probs = {k: raw[k] / total for k in raw}
        probs.setdefault('draw', None)
        probs['margin'] = total - 1.0 if len(raw) == 3 else None
        return probs

    def _attach_probabilities(self, fixture, selections):
        probs = self.implied_probabilities(fixture)
        for sel in selections:
            sel['win_prob'] = None
            if not probs:
                continue
            name = sel['selection']
            if name == Config.SELECTION_HOME_WIN:
                sel['win_prob'] = probs['home']
            elif name == Config.SELECTION_AWAY_WIN:
                sel['win_prob'] = probs['away']
            elif name == Config.SELECTION_1X and probs['draw'] is not None:
                sel['win_prob'] = probs['home'] + probs['draw']
            elif name == Config.SELECTION_X2 and probs['draw'] is not None:
                sel['win_prob'] = probs['away'] + probs['draw']
            sel['margin'] = probs.get('margin')

    def _calculate_double_chance_odds(self, odds1, odds2):
        """Calculate double chance odds from two individual odds"""
        # Formula: (odds1 * odds2) / (odds1 + odds2)
        try:
            return (odds1 * odds2) / (odds1 + odds2)
        except:
            return min(odds1, odds2)  # Fallback
    
    def _meets_criteria(self, selection):
        """Check if selection meets user criteria"""
        # Check odds range only - payout will be checked at combination level
        if not (self.min_odds <= selection['odds'] <= self.max_odds):
            return False
        
        # Only keep selections the market itself rates as likely
        prob = selection.get('win_prob')
        if prob is None or prob < self.min_win_prob:
            return False
        
        return True
    
    def _calculate_confidence(self, selection):
        """Confidence label from market-implied probability (margin removed).
        This is the bookmaker's own estimate - not an independent prediction."""
        p = selection['win_prob']
        if p >= 0.75:
            label = 'High'
        elif p >= 0.65:
            label = 'Good'
        else:
            label = 'Moderate'
        return f"{label} (~{p*100:.0f}% implied chance)"
    
    def _get_selection_reason(self, selection):
        """Explain why the selection passed the filter"""
        reasons = [f"Implied win chance {selection['win_prob']*100:.0f}% (>= {self.min_win_prob*100:.0f}% required)"]
        if selection['odds'] <= 1.50:
            reasons.append('Strong favourite')
        if selection['market'] == Config.MARKET_DOUBLE_CHANCE:
            reasons.append('Double chance' + (' (odds calculated from 1X2)' if selection.get('derived', True) else ''))
        return ' | '.join(reasons)

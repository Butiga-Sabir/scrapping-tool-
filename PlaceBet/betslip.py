"""
Bet slip management module
Handles bet slip creation, modification, and confirmation
"""
import logging
from calculator import PayoutCalculator
from config import Config

logger = logging.getLogger(__name__)

class BetSlip:
    """Manages bet slip operations"""
    
    def __init__(self, selections, stake, bet_type='Accumulator'):
        self.selections = selections
        self.stake = stake
        self.bet_type = bet_type
        self.metrics = {}
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """Calculate bet slip metrics"""
        self.metrics = PayoutCalculator.calculate_combination_metrics(
            self.selections, self.stake
        )
    
    def add_selection(self, selection):
        """Add a selection to the bet slip"""
        self.selections.append(selection)
        self._calculate_metrics()
    
    def remove_selection(self, index):
        """Remove a selection by index"""
        if 0 <= index < len(self.selections):
            removed = self.selections.pop(index)
            self._calculate_metrics()
            return removed
        return None
    
    def replace_selection(self, index, new_selection):
        """Replace a selection at index"""
        if 0 <= index < len(self.selections):
            old = self.selections[index]
            self.selections[index] = new_selection
            self._calculate_metrics()
            return old
        return None
    
    def get_summary(self):
        """Get bet slip summary"""
        return {
            'bet_type': self.bet_type,
            'matches_count': len(self.selections),
            'stake': self.stake,
            'combined_odds': self.metrics['combined_odds'],
            'potential_return': self.metrics['estimated_return'],
            'potential_profit': self.metrics['profit'],
            'roi_percentage': self.metrics['roi_percentage']
        }
    
    def display(self):
        """Display bet slip in formatted format"""
        print(f"\n{'='*50}")
        print(f"BET SLIP")
        print(f"{'='*50}")
        print(f"Bet type: {self.bet_type}")
        print(f"Matches: {len(self.selections)}")
        print(f"Stake: {PayoutCalculator.format_currency(self.stake)}")
        print(f"Combined odds: {PayoutCalculator.format_odds(self.metrics['combined_odds'])}")
        print(f"Potential return: {PayoutCalculator.format_currency(self.metrics['estimated_return'])}")
        print(f"Potential profit: {PayoutCalculator.format_currency(self.metrics['profit'])}")
        print(f"ROI: {self.metrics['roi_percentage']:.1f}%")
        print(f"\nSelections:")
        
        for i, selection in enumerate(self.selections, 1):
            print(f"{i}. {selection['home_team']} vs {selection['away_team']} — "
                  f"{selection['selection']} — {PayoutCalculator.format_odds(selection['odds'])}")
        
        print(f"{'='*50}")
    
    def to_dict(self):
        """Convert bet slip to dictionary for storage"""
        return {
            'bet_type': self.bet_type,
            'matches_count': len(self.selections),
            'stake': self.stake,
            'combined_odds': self.metrics['combined_odds'],
            'potential_return': self.metrics['estimated_return'],
            'potential_profit': self.metrics['profit'],
            'selections': self.selections
        }
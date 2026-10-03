"""
Payout calculator module
Calculates combined odds, estimated returns, and profits
"""
import logging

logger = logging.getLogger(__name__)

class PayoutCalculator:
    """Calculates betting payouts and profits"""
    
    @staticmethod
    def calculate_combined_odds(selections):
        """Calculate combined odds for multiple selections"""
        combined_odds = 1.0
        
        for selection in selections:
            combined_odds *= selection['odds']
        
        return combined_odds
    
    @staticmethod
    def calculate_estimated_return(stake, combined_odds):
        """Calculate estimated return"""
        return stake * combined_odds
    
    @staticmethod
    def calculate_profit(estimated_return, stake):
        """Calculate potential profit"""
        return estimated_return - stake
    
    @staticmethod
    def calculate_combination_metrics(combination, stake):
        """Calculate all metrics for a combination"""
        combined_odds = PayoutCalculator.calculate_combined_odds(combination)
        estimated_return = PayoutCalculator.calculate_estimated_return(stake, combined_odds)
        profit = PayoutCalculator.calculate_profit(estimated_return, stake)
        
        return {
            'combined_odds': combined_odds,
            'estimated_return': estimated_return,
            'profit': profit,
            'roi_percentage': (profit / stake) * 100 if stake > 0 else 0
        }
    
    @staticmethod
    def format_currency(amount, currency='UGX'):
        """Format amount as currency"""
        return f"{currency} {amount:,.0f}"
    
    @staticmethod
    def format_odds(odds):
        """Format odds for display"""
        return f"{odds:.2f}"
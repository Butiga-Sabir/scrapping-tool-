"""
BetPawa interface module
Handles manual interaction with BetPawa - uses Selenium to populate betslip, manual final placement
"""
import logging
from config import Config
from calculator import PayoutCalculator
from odds_provider import OddsProvider

logger = logging.getLogger(__name__)

class BetPawaInterface:
    """Manual BetPawa interface - Selenium populates betslip, user completes final placement"""
    
    def __init__(self):
        self.odds_provider = OddsProvider()
    
    def prepare_betpawa_for_manual_placement(self, bet_slip):
        """
        Prepare BetPawa for manual bet placement
        Uses Selenium to populate betslip with selections, then stops for manual final placement
        """
        try:
            logger.info("Preparing BetPawa for manual placement with Selenium")
            
            # Get market type from user preferences or default to 1X2
            from config import Config
            market_type = '1X2'  # Default to 1X2 market which has all options
            
            # Convert betslip selections to format expected by odds_provider
            selections_for_selenium = []
            for selection in bet_slip.selections:
                selections_for_selenium.append({
                    'home_team': selection['home_team'],
                    'away_team': selection['away_team'],
                    'odds': selection['odds'],
                    'selection': selection['selection']
                })
            
            # Display instructions
            self._display_manual_instructions(bet_slip)
            
            # Use Selenium to populate betslip
            print("\nUsing Selenium to populate betslip...")
            success = self.odds_provider.populate_betslip_with_selections(selections_for_selenium, market_type)
            
            if success:
                print("\n" + "="*60)
                print("SUCCESS: BETSLIP POPULATION COMPLETE")
                print("="*60)
                print("\nThe Selenium browser is now open with BetPawa.")
                print("Your selections have been added to the betslip.")
                print("\n" + "="*60)
                print("VERIFICATION STEPS")
                print("="*60)
                print("1. Check the betslip on the right side or bottom of the page")
                print("2. Verify all your selections are listed")
                print("3. Confirm the odds match your expected values")
                print("4. Check the combined odds and potential return")
                print("5. If any selections are missing, add them manually")
                print("\n" + "="*60)
                print("MANUAL FINAL PLACEMENT INSTRUCTIONS")
                print("="*60)
                print("1. Review the betslip to confirm all selections are correct")
                print("2. Verify the stake amount")
                print("3. Check the combined odds and potential return")
                print("4. Manually click 'Place Bet' or 'Confirm' to complete the bet")
                print("\n" + "="*60)
                print("IMPORTANT REMINDER")
                print("="*60)
                print("This tool will NEVER automatically click the final 'Place Bet' button.")
                print("You must complete the final placement step manually.")
                print("="*60)
                
                # Wait for user to complete manual placement
                self._wait_for_manual_completion()
            else:
                print("\n⚠️  WARNING: Could not automatically populate betslip")
                print("The browser is open with BetPawa.")
                print("You will need to manually find and select the matches.")
                self._display_manual_fallback_instructions(bet_slip)
                self._wait_for_manual_completion()
            
        except Exception as e:
            logger.error(f"Error preparing BetPawa: {e}")
            raise
    
    def _display_manual_instructions(self, bet_slip):
        """Display manual placement instructions"""
        print("\n" + "="*60)
        print("MANUAL BET PLACEMENT INSTRUCTIONS")
        print("="*60)
        print("\n✓ Selenium will open BetPawa and populate your betslip")
        print("✓ Your bet slip details are shown below")
        print("\nIMPORTANT SECURITY NOTICE:")
        print("- Selenium will click the odds buttons to add selections")
        print("- You must manually log in to BetPawa (if not already logged in)")
        print("- You must manually review your betslip")
        print("- You must manually click 'Place Bet' or 'Confirm'")
        print("\n" + "="*60)
        print("YOUR BET SLIP DETAILS:")
        print("="*60)
        
        # Display bet slip
        bet_slip.display()
        
        print("\n" + "="*60)
        print("AUTOMATED BETSLIP POPULATION")
        print("="*60)
        print("Selenium will automatically:")
        print("1. Open BetPawa in your browser")
        print("2. Navigate to the appropriate market")
        print("3. Find and click the odds buttons for your selections")
        print("4. Add selections to your betslip")
        print("\nYou will then manually:")
        print("1. Review the betslip")
        print("2. Verify the stake and odds")
        print("3. Click 'Place Bet' or 'Confirm'")
        print("="*60)
    
    def _display_manual_fallback_instructions(self, bet_slip):
        """Display manual fallback instructions when automation fails"""
        print("\n" + "="*60)
        print("MANUAL FALLBACK INSTRUCTIONS")
        print("="*60)
        print("Selenium could not automatically populate the betslip.")
        print("You will need to manually find and select the matches.")
        print("\nPlease manually:")
        print("1. Navigate to Football/Upcoming matches")
        print("2. Find the following matches and click the specified odds:")
        
        for i, selection in enumerate(bet_slip.selections, 1):
            print(f"   {i}. {selection['home_team']} vs {selection['away_team']}")
            print(f"      Selection: {selection['selection']}")
            print(f"      Odds: {selection['odds']:.2f}")
        
        print("3. Review your betslip to confirm:")
        print(f"   - Total stake: {bet_slip.stake:,}")
        print(f"   - Combined odds: {bet_slip.metrics['combined_odds']:.2f}")
        print(f"   - Potential return: {bet_slip.metrics['estimated_return']:,.0f}")
        print("4. Click 'Place Bet' or 'Confirm' MANUALLY")
        print("="*60)
    
    def _wait_for_manual_completion(self):
        """Wait for user to complete manual placement"""
        print("\nWaiting for you to complete manual bet placement...")
        print("Press Enter in this terminal when you have finished:")
        
        input()  # Wait for user to press Enter
        
        print("\nManual placement step completed.")
        logger.info("User completed manual bet placement")
    
    def get_manual_placement_confirmation(self, bet_slip):
        """
        Get final confirmation before opening BetPawa
        This is the final safety check before manual placement
        """
        print("\n" + "="*60)
        print("FINAL BET CONFIRMATION")
        print("="*60)
        
        summary = bet_slip.get_summary()
        
        print(f"Bet type: {summary['bet_type']}")
        print(f"Matches: {summary['matches_count']}")
        print(f"Stake: {PayoutCalculator.format_currency(summary['stake'])}")
        print(f"Combined odds: {PayoutCalculator.format_odds(summary['combined_odds'])}")
        print(f"Potential return: {PayoutCalculator.format_currency(summary['potential_return'])}")
        print(f"Potential profit: {PayoutCalculator.format_currency(summary['potential_profit'])}")
        
        print("\nSelections:")
        for i, selection in enumerate(bet_slip.selections, 1):
            print(f"{i}. {selection['home_team']} vs {selection['away_team']} — "
                  f"{selection['selection']} — {PayoutCalculator.format_odds(selection['odds'])}")
        
        print("\n" + "="*60)
        print("WHAT WILL HAPPEN NEXT:")
        print("="*60)
        print("1. Selenium will open BetPawa in your browser")
        print("2. Selenium will automatically find and click the odds buttons")
        print("3. Selections will be added to your betslip")
        print("4. YOU will manually review and click 'Place Bet'")
        print("\n" + "="*60)
        
        response = input("Do you want to continue to BetPawa and place this bet manually? [Y/N]: ").strip().upper()
        
        return response == 'Y'
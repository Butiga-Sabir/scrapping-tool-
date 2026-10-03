"""
Main application with interactive setup wizard
BetPawa Betting Assistant - Manual confirmation required for final placement
"""
import logging
import sys
import traceback
from config import Config
from database import DatabaseManager
from odds_provider import OddsProvider
from selector import SelectionFilter
from combinations import CombinationGenerator
from betslip import BetSlip
from betpawa_interface import BetPawaInterface
from calculator import PayoutCalculator

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=getattr(Config, 'LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
# Harmless Windows noise when chromedriver's handle is already closed at interpreter exit
logging.getLogger('selenium.webdriver.common.service').setLevel(logging.CRITICAL)

class BettingAssistant:
    """Main betting assistant application"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.odds_provider = OddsProvider()
        self.betpawa_interface = BetPawaInterface()
        self.current_bet_slip = None
        self.user_preferences = {}
    
    def run_setup_wizard(self):
        """Interactive setup wizard for user preferences"""
        print("="*60)
        print("BETPAWA BETTING ASSISTANT - SETUP WIZARD")
        print("="*60)
        print("\nThis tool finds the most probable combinations that reach your payout target.")
        print("It will NEVER automatically place bets - you must confirm final placement.")
        print("\n" + "="*60)
        
        # Get user preferences
        self._get_odds_preferences()
        self._get_payout_preferences()
        self._get_stake_preference()
        self._get_market_preference()
        self._get_probability_preference()
        self._get_selection_limits()
        
        # Display summary
        self._display_preferences_summary()
        
        # Confirm preferences
        if not self._confirm_preferences():
            print("Setup cancelled.")
            return False
        
        return True
    
    def _get_odds_preferences(self):
        """Get odds range preferences"""
        print("\n" + "-"*60)
        print("ODDS RANGE")
        print("-"*60)
        
        while True:
            try:
                min_odds = float(input("Minimum odds (e.g., 1.20): ").strip())
                max_odds = float(input("Maximum odds (e.g., 3.00): ").strip())
                
                if min_odds < 1.01 or max_odds > 50.00:
                    print("Invalid odds range. Odds must be between 1.01 and 50.00")
                    continue
                
                if min_odds >= max_odds:
                    print("Minimum odds must be less than maximum odds")
                    continue
                
                self.user_preferences['min_odds'] = min_odds
                self.user_preferences['max_odds'] = max_odds
                break
                
            except ValueError:
                print("Please enter valid decimal numbers")
    
    def _get_payout_preferences(self):
        """Get payout preferences"""
        print("\n" + "-"*60)
        print("PAYOUT REQUIREMENTS")
        print("-"*60)
        
        while True:
            try:
                min_payout = float(input("Minimum total payout/return (e.g., 50000): ").strip())
                
                if min_payout < 100:
                    print("Minimum payout must be at least 100")
                    continue
                
                self.user_preferences['min_payout'] = min_payout
                break
                
            except ValueError:
                print("Please enter a valid number")
    
    def _get_stake_preference(self):
        """Get stake amount"""
        print("\n" + "-"*60)
        print("STAKE AMOUNT")
        print("-"*60)
        
        while True:
            try:
                stake = float(input("Stake amount (e.g., 5000): ").strip())
                
                if stake < 100:
                    print("Minimum stake is 100")
                    continue
                
                self.user_preferences['stake'] = stake
                break
                
            except ValueError:
                print("Please enter a valid number")
    
    def _get_market_preference(self):
        """Get betting market type"""
        print("\n" + "-"*60)
        print("BETTING MARKET TYPE")
        print("-"*60)
        print("1. WIN")
        print("   - Home Win")
        print("   - Away Win")
        print("   (No single draws)")
        print("2. DOUBLE CHANCE")
        print("   - 1X (Home or Draw)")
        print("   - X2 (Away or Draw)")
        print("   (No 12 separate)")
        print("3. MIXED")
        print("   - Allow WIN and DOUBLE CHANCE selections together")
        print("   (Home Win, Away Win, 1X, X2 only)")
        
        while True:
            choice = input("Select market type (1-3): ").strip()
            
            if choice == '1':
                self.user_preferences['market_type'] = Config.MARKET_WIN
                self.user_preferences['exclude_draws'] = True  # No draws
                break
            elif choice == '2':
                self.user_preferences['market_type'] = Config.MARKET_DOUBLE_CHANCE
                self.user_preferences['exclude_draws'] = True
                break
            elif choice == '3':
                self.user_preferences['market_type'] = Config.MARKET_MIXED
                self.user_preferences['exclude_draws'] = True  # No draws in mixed either
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3")
    
    def _get_probability_preference(self):
        """Minimum market-implied win probability per selection"""
        print("\n" + "-"*60)
        print("MINIMUM WIN PROBABILITY PER MATCH")
        print("-"*60)
        print("Only matches the market rates at or above this chance are used.")
        print("Higher = safer legs, but lower odds (so more legs to reach your payout).")
        default = int(Config.DEFAULT_MIN_WIN_PROB * 100)
        
        while True:
            raw = input(f"Minimum win probability % (default {default}): ").strip()
            if not raw:
                pct = default
            else:
                try:
                    pct = float(raw)
                except ValueError:
                    print("Please enter a number, e.g. 65")
                    continue
            if not (30 <= pct <= 95):
                print("Enter a value between 30 and 95")
                continue
            self.user_preferences['min_win_prob'] = pct / 100.0
            break
    
    def _get_selection_limits(self):
        """Get selection limits - simplified, auto-calculate matches"""
        print("\n" + "-"*60)
        print("SELECTION LIMITS")
        print("-"*60)
        print("Matches will be automatically added until payout requirement is met.")
        print("Maximum combinations will be set to 5 by default.")
        
        self.user_preferences['max_matches'] = 20  # classic (manual fixtures) mode only
        self.user_preferences['max_combinations'] = 5  # classic mode only
        
        default = Config.LIVE_MAX_LEGS
        while True:
            raw = input(f"Maximum matches in the slip (default {default}): ").strip()
            if not raw:
                self.user_preferences['max_legs'] = default
                break
            if raw.isdigit() and 1 <= int(raw) <= 200:
                self.user_preferences['max_legs'] = int(raw)
                break
            print("Enter a whole number between 1 and 200")
    
    def _display_preferences_summary(self):
        """Display summary of user preferences"""
        print("\n" + "="*60)
        print("PREFERENCES SUMMARY")
        print("="*60)
        print(f"Odds Range: {self.user_preferences['min_odds']:.2f} - {self.user_preferences['max_odds']:.2f}")
        print(f"Minimum Payout: {self.user_preferences['min_payout']:,.0f}")
        print(f"Stake: {self.user_preferences['stake']:,.0f}")
        print(f"Market Type: {self.user_preferences['market_type']}")
        print(f"Min win probability per match: {self.user_preferences['min_win_prob']*100:.0f}%")
        print(f"Combinations will auto-add matches until payout requirement is met")
        print("="*60)
    
    def _confirm_preferences(self):
        """Confirm user preferences"""
        print("\nDo you want to proceed with these preferences?")
        choice = input("Enter 'Y' to continue or 'N' to modify: ").strip().upper()
        return choice == 'Y'
    
    def fetch_and_process_odds(self):
        """Fetch odds and process them"""
        print("\n" + "="*60)
        print("FETCHING ODDS FROM BETPAWA")
        print("="*60)
        
        fixtures = self.odds_provider.fetch_odds_from_betpawa()
        
        if not fixtures:
            print("No fixtures available from BetPawa.")
            print("This could be due to:")
            print("- Internet connection issues")
            print("- BetPawa website changes")
            print("- Anti-bot detection")
            print(f"\nDebug files (screenshot + page text) were saved in '{Config.DEBUG_DIR}/'.")
            print("If BetPawa shows a challenge/block page in the browser, this tool will not bypass it.")
            choice = input("\nEnter fixtures manually instead? (y/n): ").strip().lower()
            if choice != 'y':
                return None
            fixtures = self.odds_provider.get_manual_odds_input()
            if not fixtures:
                return None
        
        return self.process_fixtures(fixtures)
    
    def process_fixtures(self, fixtures):
        """Filter a list of fixtures into qualifying selections (classic mode)"""
        print("\n" + "="*60)
        print("FILTERING SELECTIONS")
        print("="*60)
        
        selector = SelectionFilter(
            self.user_preferences['min_odds'],
            self.user_preferences['max_odds'],
            self.user_preferences['min_payout'],
            self.user_preferences['stake'],
            self.user_preferences['market_type'],
            self.user_preferences['exclude_draws'],
            self.user_preferences['min_win_prob']
        )
        
        filtered_selections = selector.filter_fixtures(fixtures)
        
        if not filtered_selections:
            print("No selections meet your criteria. Try adjusting your preferences.")
            return None
        
        print(f"\nFound {len(filtered_selections)} qualifying selections")
        return filtered_selections
    
    def generate_combinations(self, selections):
        """Generate betting combinations"""
        print("\n" + "="*60)
        print("GENERATING COMBINATIONS")
        print("="*60)
        print(f"Automatically adding matches until payout requirement ({self.user_preferences['min_payout']:,.0f}) is met...")
        
        generator = CombinationGenerator(
            self.user_preferences['max_matches'],
            self.user_preferences['max_combinations']
        )
        
        combinations = generator.generate_combinations(
            selections, 
            self.user_preferences['min_payout'],
            self.user_preferences['stake']
        )
        
        if not combinations:
            print("No valid combinations generated.")
            print("Try adjusting your odds range or stake to meet the payout requirement.")
            return None
        
        if not generator.meets_payout:
            print("\nWARNING: With your win-probability filter, no slip reaches the payout target.")
            print("Showing the best available slip instead. Lower the probability floor or the payout target.")
        
        # Highest chance of winning first
        combinations = generator.sort_combinations_by_probability(combinations)
        
        print(f"Generated {len(combinations)} combinations")
        return combinations
    
    def display_combination(self, combination, index):
        """Display a single combination"""
        print(f"\n{'='*60}")
        print(f"BET SLIP {index}")
        print(f"{'='*60}")
        
        for i, selection in enumerate(combination, 1):
            print(f"{i}. {selection['home_team']} vs {selection['away_team']} — "
                  f"{selection['selection']} — {PayoutCalculator.format_odds(selection['odds'])}")
        
        # Calculate metrics
        metrics = PayoutCalculator.calculate_combination_metrics(combination, self.user_preferences['stake'])
        
        print(f"\nCombined odds: {PayoutCalculator.format_odds(metrics['combined_odds'])}")
        print(f"Stake: {PayoutCalculator.format_currency(self.user_preferences['stake'])}")
        print(f"Chance all legs win (market-implied): {CombinationGenerator.combined_probability(combination)*100:.1f}%")
        print(f"Potential return: {PayoutCalculator.format_currency(metrics['estimated_return'])}")
        print(f"Potential profit: {PayoutCalculator.format_currency(metrics['profit'])}")
        
        # Show additional details
        print(f"\nSelection Details:")
        for i, selection in enumerate(combination, 1):
            print(f"{i}. Competition: {selection['competition']}")
            print(f"   Date/Time: {selection['date_time']}")
            print(f"   Selection: {selection['selection']}")
            print(f"   Odds: {PayoutCalculator.format_odds(selection['odds'])}")
            print(f"   Confidence: {selection.get('confidence', 'N/A')}")
            print(f"   Reason: {selection.get('reason', 'N/A')}")
    
    def interactive_combination_selection(self, combinations):
        """Simplified combination selection - show best combination directly"""
        print("\n" + "="*60)
        print("BEST COMBINATION")
        print("="*60)
        
        # Show the best combination (highest payout)
        if combinations:
            best_combination = combinations[0]
            self.display_combination(best_combination, 1)
            self.current_combination = best_combination
            
            print("\n" + "="*60)
            print("OPTIONS")
            print("="*60)
            print("[1] Accept this combination")
            print("[2] Generate new combinations with different criteria")
            print("[3] Cancel")
            
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == '1':
                return best_combination
            elif choice == '2':
                return 'generate_new'
            elif choice == '3':
                return None
            else:
                print("Invalid choice")
                return None
        
        return None
    

    
    def finalize_bet_slip(self, combination):
        """Finalize bet slip and get final confirmation"""
        print("\n" + "="*60)
        print("FINAL BET CONFIRMATION")
        print("="*60)
        
        # Create bet slip
        self.current_combination = combination
        bet_slip = BetSlip(combination, self.user_preferences['stake'])
        self.current_bet_slip = bet_slip
        
        # Display final confirmation
        bet_slip.display()
        
        # Get final confirmation
        confirmed = self.betpawa_interface.get_manual_placement_confirmation(bet_slip)
        
        if confirmed:
            # Save to database
            bet_slip_id = self.db.save_bet_slip(bet_slip.to_dict())
            print(f"\nBet slip saved to database (ID: {bet_slip_id})")
            
            # Open BetPawa for manual placement
            print("\nOpening BetPawa for manual placement...")
            self.betpawa_interface.prepare_betpawa_for_manual_placement(bet_slip)
            
            # Update status after manual placement
            self.db.update_bet_slip_status(bet_slip_id, 'placed', 'User confirmed and manually placed')
            
            print("\nBet slip marked as 'placed' in database.")
        else:
            print("\nBet placement cancelled.")
            if self.current_bet_slip:
                bet_slip_id = self.db.save_bet_slip(self.current_bet_slip.to_dict())
                self.db.update_bet_slip_status(bet_slip_id, 'cancelled', 'User cancelled during confirmation')
    
    def run_live(self):
        """Streaming mode: scroll BetPawa and add fitting selections to the betslip as they appear."""
        prefs = self.user_preferences
        print("\n" + "="*60)
        print("LIVE BUILD - ADDING MATCHES TO THE BETSLIP AS THEY ARE FOUND")
        print("="*60)
        if prefs['market_type'] == Config.MARKET_DOUBLE_CHANCE:
            print("Market: Double Chance (1X / X2). Tip: these odds are low (often 1.05-1.40),")
            print("so keep your minimum odds at ~1.05 or most matches will be filtered out.")
        elif prefs['market_type'] == Config.MARKET_MIXED:
            print("Market: MIXED - Home/Away wins first, then Double Chance (1X / X2) if more legs are needed.")
        print(f"Target: return >= {prefs['min_payout']:,.0f} on stake {prefs['stake']:,.0f} "
              f"(combined odds >= {prefs['min_payout']/prefs['stake']:.2f})")
        print("A browser window will open - leave it alone while it works.\n")

        max_legs = prefs.get('max_legs', Config.LIVE_MAX_LEGS)
        target_odds = prefs['min_payout'] / prefs['stake']
        needed_avg = target_odds ** (1.0 / max_legs)
        print(f"Leg cap: {max_legs}  |  legs must average odds >= {needed_avg:.3f} to reach the target")
        if needed_avg > prefs['max_odds']:
            print(f"WARNING: even {max_legs} legs at your maximum odds ({prefs['max_odds']}) can't reach "
                  f"{target_odds:.0f}x. Raise the leg cap, the max odds, or lower the target.")

        selector = SelectionFilter(
            prefs['min_odds'], prefs['max_odds'], prefs['min_payout'], prefs['stake'],
            prefs['market_type'], True, prefs['min_win_prob'])

        leg_counter = {'n': 0}

        def on_added(sel, running_odds, checked):
            leg_counter['n'] += 1
            meaning = {'1X': f"{sel['home_team']} or Draw", 'X2': f"Draw or {sel['away_team']}"}.get(sel['selection'])
            label = f"{sel['selection']} ({meaning})" if meaning else sel['selection']
            print(f"+ [{leg_counter['n']}/{max_legs}] {sel['home_team']} vs {sel['away_team']} - {label} @ "
                  f"{sel['odds']:.2f} ({sel['win_prob']*100:.0f}%)  |  "
                  f"running odds {running_odds:.2f}  |  return "
                  f"{PayoutCalculator.format_currency(running_odds * prefs['stake'])}  "
                  f"[{checked} matches checked]")

        result = self.odds_provider.build_betslip_live(
            selector, prefs['stake'], prefs['min_payout'], max_legs, on_added)

        for note in result.get('notes', []):
            print(f"\nNOTE: {note}")
        if result['status'] != 'ok' or not result['added']:
            return result
        
        added = result['added']
        slip = BetSlip(added, prefs['stake'])
        self.current_bet_slip = slip
        slip_id = self.db.save_bet_slip(slip.to_dict())
        self.db.update_bet_slip_status(slip_id, 'pending', 'Populated in betslip, awaiting manual placement')

        chance = 1.0
        for s in added:
            chance *= s.get('win_prob') or 0.0
        print("\n" + "="*60)
        if result['reached_target']:
            print("TARGET REACHED - BETSLIP READY")
        elif result.get('stop_reason') == 'cap':
            print(f"LEG CAP REACHED ({max_legs} matches) - TARGET NOT REACHED")
            print(f"Combined odds {result['combined_odds']:.2f} vs {target_odds:.2f} needed. "
                  "Raise the maximum matches, allow higher max odds, or lower the payout target.")
        else:
            print("RAN OUT OF MATCHES - TARGET NOT REACHED")
            print(f"Checked {result['fixtures_checked']} matches, {len(added)} met your criteria.")
            print(f"Combined odds {result['combined_odds']:.2f} vs {target_odds:.2f} needed. "
                  "Lower the probability floor, widen the odds range, or lower the payout target.")
        print(f"Chance every leg wins (market-implied): {chance*100:.4f}%")
        print("="*60)
        slip.display()
        print("\nThe browser stays open - review the betslip and click 'Place Bet' yourself.")
        print("This tool never presses the final button and never closes the browser.")
        answer = input("\nWhen you're finished there: did you place the bet? (y/n): ").strip().lower()
        self.db.update_bet_slip_status(slip_id, 'placed' if answer == 'y' else 'cancelled',
                                       'User confirmed placement' if answer == 'y' else 'User did not place')
        return result

    def run(self):
        """Main application runner"""
        try:
            # Run setup wizard
            if not self.run_setup_wizard():
                return
            
            # Live streaming mode: add to betslip while scrolling, no pre-scan or confirmation screens
            result = self.run_live()
            if result['status'] == 'ok':
                if not result['added'] and not result.get('notes'):
                    print(f"\nChecked {result['fixtures_checked']} matches - none met your criteria.")
                    print("Try lowering the minimum win probability or widening the odds range.")
                return
            
            # Could not read the site: offer manual entry through the classic flow
            print("\nCould not read fixtures from BetPawa "
                  f"({result['status']}). Debug files are in '{Config.DEBUG_DIR}/'.")
            print("If the browser showed a block/challenge page, this tool will not bypass it.")
            if input("Enter fixtures manually instead? (y/n): ").strip().lower() != 'y':
                return
            fixtures = self.odds_provider.get_manual_odds_input()
            selections = self.process_fixtures(fixtures) if fixtures else None
            if not selections:
                return
            combinations = self.generate_combinations(selections)
            if not combinations:
                return
            chosen = self.interactive_combination_selection(combinations)
            if chosen and chosen != 'generate_new':
                self.finalize_bet_slip(chosen)
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            logger.info("User cancelled the operation")
        except Exception as e:
            logger.error(f"Error in main application: {e}")
            logger.error(traceback.format_exc())
            print(f"\nAn error occurred: {e}")
            print("Please check the log file for details.")

def main():
    """Main entry point"""
    print("BetPawa Betting Assistant")
    print("="*60)
    print("IMPORTANT: This tool will NEVER automatically place bets.")
    print("You must manually confirm and complete the final placement.")
    print("="*60)
    
    assistant = BettingAssistant()
    assistant.run()

if __name__ == "__main__":
    main()
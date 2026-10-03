# BetPawa Betting Assistant

A Python betting assistance bot for BetPawa with Selenium automation for odds retrieval and betslip population. Manual confirmation required for final bet placement.

## IMPORTANT SAFETY FEATURES

✅ **NO AUTOMATIC BET PLACEMENT** - Tool stops at final confirmation
✅ **SELENIUM AUTOMATION** - Automatically finds odds and populates betslip
✅ **MANUAL FINAL STEP** - User must click final "Place Bet" button
✅ **NO PASSWORD STORAGE** - Credentials never stored in plaintext
✅ **NO SECURITY BYPASS** - Respects all BetPawa security controls
✅ **USER CONFIRMATION REQUIRED** - Multiple confirmation steps before final action

## INSTALLATION

```bash
pip install -r requirements.txt
```

This will install:
- `selenium` - Browser automation
- `webdriver-manager` - Automatic Chrome driver management
- `python-dotenv` - Environment configuration
- `requests` - HTTP requests

## PROJECT STRUCTURE

- `config.py` - Configuration settings
- `database.py` - SQLite database management
- `odds_provider.py` - Selenium-based odds retrieval and betslip population
- `selector.py` - Filtering and selection logic
- `combinations.py` - Combination generation
- `calculator.py` - Payout calculations
- `betslip.py` - Bet slip management
- `betpawa_interface.py` - Selenium BetPawa interface (betslip population only)
- `main.py` - Main application with setup wizard
- `.env` - Environment configuration
- `.env.example` - Environment configuration template
- `requirements.txt` - Python dependencies

## USAGE

```bash
python main.py
```

### Live build (default)
After the setup wizard the tool opens BetPawa and scrolls the match list. Every match that
fits your odds range and minimum win probability is clicked into the betslip immediately,
while it keeps checking the rest, and it stops as soon as your payout target is reached.
There is no pre-scan and no combination confirmation screen. You review the betslip and
click "Place Bet" yourself - the tool never presses that button.

Markets in live mode:
- **WIN** - Home/Away Win from the 1X2 page.
- **DOUBLE_CHANCE** - the tool switches BetPawa to its Double Chance market and clicks the real
  1X / X2 prices (12 is never used). Keep minimum odds near 1.05, since these prices are low.
- **MIXED** - wins first, then Double Chance for the remaining matches (one pick per match).

The Double Chance page is opened directly (`/events?categoryId=2&marketId=Double%20Chance`); set
`DC_MARKET_URL` in `.env` only if BetPawa changes that address. In MIXED mode the page changes after
the wins phase, so check the betslip still holds those picks.

If BetPawa can't be read, it offers manual fixture entry (classic combination flow).

## SETUP WIZARD

The tool will guide you through:

1. **Odds Range** (e.g., 1.20 - 3.00)
2. **Minimum Payout** (e.g., UGX 50,000)
3. **Stake Amount** (e.g., UGX 5,000)
4. **Market Type** (WIN, DOUBLE CHANCE, or MIXED)
5. **Selection Limits** (number of matches and combinations)

## MARKET TYPES

### WIN
- Home Win
- Away Win
- (No single draws)

### DOUBLE CHANCE
- 1X (Home or Draw)
- X2 (Away or Draw)
- (No 12 separate)

### MIXED
- Combination of WIN and DOUBLE CHANCE selections
- Home Win, Away Win, 1X, X2 only
- (No single draws, no 12 separate)

## AUTOMATION FEATURES

### Selenium-Powered Features:
1. **Automatic Odds Retrieval** - Scrapes live odds from BetPawa
2. **Automatic Betslip Population** - Clicks odds buttons to add selections
3. **Smart Selection Matching** - Finds matches by team names and odds
4. **Fallback to Manual** - If automation fails, provides manual instructions

### Manual Steps:
1. **Login** - You manually log in to BetPawa
2. **Review** - You review the populated betslip
3. **Final Placement** - You manually click "Place Bet" or "Confirm"

## CONFIDENCE INDICATORS

Based on measurable statistics (odds analysis only):
- **High** - Odds ≤ 1.30 (strong favorite)
- **Medium** - Odds ≤ 1.70 (moderate favorite)
- **Low** - Odds ≤ 2.50 (less favored)
- **Very Low** - Odds > 2.50 (underdog)

**IMPORTANT**: These are NOT win probability predictions - they indicate relative strength based on odds.

## FINAL CONFIRMATION PROCESS

1. **Accept selections** - Review and confirm the combination
2. **FINAL CONFIRMATION SCREEN** - Shows complete bet details
3. **Selenium Automation** - Opens browser and automatically:
   - Navigates to BetPawa
   - Finds matches by team names
   - Clicks odds buttons
   - Populates betslip
4. **Manual Final Step** - You manually:
   - Log in to BetPawa (if not already logged in)
   - Review the betslip
   - Verify stake and odds
   - Click "Place Bet" or "Confirm"

## DATABASE

All bet slips are saved to SQLite database with:
- Timestamp
- Selections
- Stake and odds
- Status (pending/placed/cancelled)
- Results tracking

## LOGGING

All operations are logged to `betting_assistant.log` for:
- Debugging
- Audit trail
- Error tracking

## DISCLAIMER

This tool is for betting assistance only. No selections are guaranteed to win. Bet responsibly and within your means.
"""
Configuration module for BetPawa Betting Assistant
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'betting_assistant.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'betting_assistant.log')
    
    # BetPawa
    BETPAWA_URL = os.getenv('BETPAWA_URL', 'https://www.betpawa.ug')
    
    # Default betting parameters
    DEFAULT_STAKE = float(os.getenv('DEFAULT_STAKE', '5000'))
    DEFAULT_MIN_ODDS = float(os.getenv('DEFAULT_MIN_ODDS', '1.20'))
    DEFAULT_MAX_ODDS = float(os.getenv('DEFAULT_MAX_ODDS', '3.00'))
    DEFAULT_MIN_PAYOUT = float(os.getenv('DEFAULT_MIN_PAYOUT', '50000'))
    
    # Selection limits
    DEFAULT_MAX_MATCHES = int(os.getenv('DEFAULT_MAX_MATCHES', '5'))
    DEFAULT_MAX_COMBINATIONS = int(os.getenv('DEFAULT_MAX_COMBINATIONS', '10'))
    
    # Probability-based selection (market-implied, margin removed)
    DEFAULT_MIN_WIN_PROB = float(os.getenv('DEFAULT_MIN_WIN_PROB', '0.60'))
    MAX_LEGS = int(os.getenv('MAX_LEGS', '8'))            # max matches per slip (classic combination mode)
    LIVE_MAX_LEGS = int(os.getenv('LIVE_MAX_LEGS', '60')) # default max matches per slip (live build)
    LIVE_PACE = os.getenv('LIVE_PACE', 'true').lower() == 'true'   # skip legs too low to reach the target within the leg cap
    POOL_SIZE = int(os.getenv('POOL_SIZE', '20'))         # best N selections considered for combos

    # Browser
    HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'   # headed is far less likely to be blocked
    DEBUG_DIR = os.getenv('DEBUG_DIR', 'debug')

    # BetPawa's Double Chance page (confirmed address). Override in .env if BetPawa changes it.
    DC_MARKET_URL = os.getenv('DC_MARKET_URL') or f"{BETPAWA_URL}/events?categoryId=2&marketId=Double%20Chance"

    # Lazy-load scrolling
    SCROLL_LOAD_WAIT = float(os.getenv('SCROLL_LOAD_WAIT', '6'))    # seconds to wait for next batch after each scroll
    SCROLL_MAX_STALLS = int(os.getenv('SCROLL_MAX_STALLS', '3'))    # consecutive empty waits before stopping
    SCROLL_MAX_STEPS = int(os.getenv('SCROLL_MAX_STEPS', '150'))    # hard cap on scroll steps
    MAX_FIXTURES = int(os.getenv('MAX_FIXTURES', '400'))            # stop once this many matches are collected

    # Market types
    MARKET_WIN = 'WIN'
    MARKET_DOUBLE_CHANCE = 'DOUBLE_CHANCE'
    MARKET_MIXED = 'MIXED'
    
    # Market type mapping to BetPawa URLs
    MARKET_URL_MAPPING = {
        'WIN': '1X2',
        'DOUBLE_CHANCE': '1X2',  # Use 1X2 for double chance (all selections available)
        'MIXED': '1X2'  # Use 1X2 for mixed (all selections available)
    }
    
    # Selection types
    SELECTION_HOME_WIN = 'Home Win'
    SELECTION_DRAW = 'Draw'
    SELECTION_AWAY_WIN = 'Away Win'
    SELECTION_1X = '1X'
    SELECTION_X2 = 'X2'
    SELECTION_12 = '12'
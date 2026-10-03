"""
Database module for SQLite operations
Handles saved selections and betting history
"""
import sqlite3
import json
from datetime import datetime
from config import Config

class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create bet_slips table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bet_slips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bet_type TEXT,
                matches_count INTEGER,
                stake REAL,
                combined_odds REAL,
                potential_return REAL,
                potential_profit REAL,
                selections_json TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT
            )
        ''')
        
        # Create betting_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS betting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bet_slip_id INTEGER,
                placed_at TIMESTAMP,
                actual_return REAL,
                actual_profit REAL,
                result TEXT,
                FOREIGN KEY (bet_slip_id) REFERENCES bet_slips(id)
            )
        ''')
        
        # Create fixtures table for caching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fixtures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition TEXT,
                date_time TEXT,
                home_team TEXT,
                away_team TEXT,
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_bet_slip(self, bet_slip):
        """Save a bet slip to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bet_slips 
            (bet_type, matches_count, stake, combined_odds, potential_return, potential_profit, selections_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bet_slip['bet_type'],
            bet_slip['matches_count'],
            bet_slip['stake'],
            bet_slip['combined_odds'],
            bet_slip['potential_return'],
            bet_slip['potential_profit'],
            json.dumps(bet_slip['selections']),
            'pending'
        ))
        
        bet_slip_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return bet_slip_id
    
    def update_bet_slip_status(self, bet_slip_id, status, notes=None):
        """Update bet slip status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if notes:
            cursor.execute('''
                UPDATE bet_slips 
                SET status = ?, notes = ?
                WHERE id = ?
            ''', (status, notes, bet_slip_id))
        else:
            cursor.execute('''
                UPDATE bet_slips 
                SET status = ?
                WHERE id = ?
            ''', (status, bet_slip_id))
        
        conn.commit()
        conn.close()
    
    def get_pending_bet_slips(self):
        """Get all pending bet slips"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, created_at, bet_type, matches_count, stake, combined_odds, 
                   potential_return, potential_profit, selections_json, status
            FROM bet_slips
            WHERE status = 'pending'
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        bet_slips = []
        for row in rows:
            bet_slips.append({
                'id': row[0],
                'created_at': row[1],
                'bet_type': row[2],
                'matches_count': row[3],
                'stake': row[4],
                'combined_odds': row[5],
                'potential_return': row[6],
                'potential_profit': row[7],
                'selections': json.loads(row[8]),
                'status': row[9]
            })
        
        return bet_slips
    
    def save_fixture(self, fixture):
        """Save fixture data to cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO fixtures 
            (competition, date_time, home_team, away_team, home_odds, draw_odds, away_odds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            fixture['competition'],
            fixture['date_time'],
            fixture['home_team'],
            fixture['away_team'],
            fixture['home_odds'],
            fixture['draw_odds'],
            fixture['away_odds']
        ))
        
        conn.commit()
        conn.close()
    
    def get_cached_fixtures(self, hours_old=1):
        """Get cached fixtures from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT competition, date_time, home_team, away_team, home_odds, draw_odds, away_odds
            FROM fixtures
            WHERE datetime(timestamp) > datetime('now', '-' || ? || ' hours')
            ORDER BY date_time
        ''', (hours_old,))
        
        rows = cursor.fetchall()
        conn.close()
        
        fixtures = []
        for row in rows:
            fixtures.append({
                'competition': row[0],
                'date_time': row[1],
                'home_team': row[2],
                'away_team': row[3],
                'home_odds': row[4],
                'draw_odds': row[5],
                'away_odds': row[6]
            })
        
        return fixtures
"""
Fixture parser for BetPawa's rendered page text.

BetPawa is a JavaScript single-page app and does NOT print "Team A vs Team B".
Each event is rendered as a block of lines, roughly:

    England - Premier League      <- competition header (sometimes)
    Today 20:00                   <- kick-off
    Chelsea                       <- home
    Fulham                        <- away
    +312                          <- number of extra markets
    1.45   4.50   6.80            <- 1 / X / 2 odds

Instead of depending on CSS classes (which change with every deploy), we parse
`document.body.innerText` structurally: find every run of three decimal odds,
then read the team names from the lines just before it.

Pure functions only, so it can be unit-tested without a browser.
"""
import re
from typing import Dict, List, Optional

ODDS_RE = re.compile(r'^\d{1,3}\.\d{2}$')
EXTRA_MARKETS_RE = re.compile(r'^\+\s*\d+$')
TIME_RE = re.compile(r'\b\d{1,2}:\d{2}\b')
DATE_WORDS = ('today', 'tomorrow', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
OUTCOME_LABELS = {'1', 'x', '2', '1x', '12', 'x2'}   # 1X2 and Double Chance column headers
NOISE_LINES = {'live', 'ht', 'ft', 'upcoming', 'popular', 'all', 'more', 'suspended'}
VS_SPLIT_RE = re.compile(r'\s+(?:vs\.?|v)\s+', re.IGNORECASE)


def _is_odds(line: str) -> bool:
    if not ODDS_RE.match(line):
        return False
    return 1.01 <= float(line) <= 500.0


def _looks_like_time(line: str) -> bool:
    low = line.lower()
    return bool(TIME_RE.search(line)) or low.split(' ')[0] in DATE_WORDS


def _is_breadcrumb(line: str) -> bool:
    """Competition breadcrumbs look like 'Football / Malaysia / Malaysia Presidents Cup U20'."""
    return ' / ' in line


def _is_name(line: str) -> bool:
    """A candidate team line: has letters, not a number/time/noise/breadcrumb."""
    low = line.lower()
    if _is_breadcrumb(line):
        return False
    if low in NOISE_LINES or low in OUTCOME_LABELS:
        return False
    if EXTRA_MARKETS_RE.match(line) or _is_odds(line) or _looks_like_time(line):
        return False
    if not re.search(r'[A-Za-z]', line):
        return False
    return 2 <= len(line) <= 60


DC_LABELS = {'1x', '12', 'x2'}
DC_DEFAULT_ORDER = ['1x', 'x2', '12']   # BetPawa's real column order (confirmed by user)


def detect_dc_column_order(lines: List[str]) -> Optional[List[str]]:
    """Read the Double Chance column order from the header: three consecutive lines that are
    1X, 12 and X2 in some order. Returns e.g. ['1x', 'x2', '12'] or None if not found."""
    for i in range(len(lines) - 2):
        trio = [ln.lower() for ln in lines[i:i + 3]]
        if set(trio) == DC_LABELS:
            return trio
    return None


def _take_odds_triplet(lines: List[str], i: int):
    """Starting at index i, read three odds (skipping 1/X/2 labels).
    Returns (odds, labels, next_index); labels[k] is the label line seen just before odds[k]
    (or None). Returns (None, None, i) if there are not three prices."""
    odds, labels, j, last_label = [], [], i, None
    while j < len(lines) and len(odds) < 3:
        line = lines[j]
        if _is_odds(line):
            odds.append(float(line))
            labels.append(last_label)
            last_label = None
        elif line.lower() in OUTCOME_LABELS:
            last_label = line.lower()
        else:
            break
        j += 1
    return (odds, labels, j) if len(odds) == 3 else (None, None, i)


def parse_fixtures_from_text(page_text: str, market: str = '1X2') -> List[Dict]:
    """Parse rendered page text into fixtures.
    market='1X2': odds order is 1, X, 2.  market='DC': odds order is 1X, X2, 12."""
    lines = [ln.strip() for ln in page_text.replace('\r', '').split('\n')]
    lines = [ln for ln in lines if ln]

    fixtures: List[Dict] = []
    seen = set()
    pending: List[str] = []   # lines since the last fixture ended
    last_competition = 'Unknown Competition'   # headers appear once per group of events
    header_order = detect_dc_column_order(lines) if market == 'DC' else None
    i = 0

    while i < len(lines):
        line = lines[i]

        # An odds triplet can only start on an odds line or a 1/X/2 label line
        if _is_odds(line) or line.lower() in OUTCOME_LABELS:
            odds, labels, nxt = _take_odds_triplet(lines, i)
            if odds:
                fixture = _build_fixture(pending, odds, last_competition, market, labels, header_order)
                if fixture:
                    last_competition = fixture['competition']
                    key = (fixture['home_team'].lower(), fixture['away_team'].lower())
                    if key not in seen:
                        seen.add(key)
                        fixtures.append(fixture)
                pending = []
                i = nxt
                continue

        pending.append(line)
        pending = pending[-12:]   # only the recent context matters
        i += 1

    return fixtures


def _build_fixture(pending: List[str], odds: List[float], default_competition: str,
                   market: str = '1X2', labels=None, header_order=None) -> Optional[Dict]:
    date_time = 'TBD'
    for ln in reversed(pending):
        if _looks_like_time(ln):
            date_time = ln
            break

    names = [ln for ln in pending if _is_name(ln)]
    if not names:
        return None
    crumbs = [ln for ln in pending if _is_breadcrumb(ln)]
    breadcrumb = crumbs[-1] if crumbs else None

    home = away = None
    competition = default_competition

    # Case 1: "Home vs Away" (or "Home v Away") on a single line
    last = names[-1]
    parts = VS_SPLIT_RE.split(last)
    if len(parts) == 2:
        home, away = parts[0].strip(), parts[1].strip()
        if len(names) >= 2:
            competition = names[-2]
    # Case 2: home and away on their own lines
    elif len(names) >= 2:
        home, away = names[-2], names[-1]
        if len(names) >= 3:
            competition = names[-3]

    if not home or not away or home.lower() == away.lower():
        return None
    if breadcrumb:
        competition = breadcrumb

    base = {
        'competition': competition,
        'date_time': date_time,
        'home_team': home,
        'away_team': away,
        'home_odds': None, 'draw_odds': None, 'away_odds': None,
        'dc_1x': None, 'dc_12': None, 'dc_x2': None,
    }
    if market == 'DC':
        # Column order: labels printed next to each price > the page header > default 1X, X2, 12.
        # Never assume position blindly - picking the wrong column would add a 12 bet.
        if labels and all(labels) and set(labels) == DC_LABELS:
            order = list(labels)
        elif header_order:
            order = list(header_order)
        else:
            order = list(DC_DEFAULT_ORDER)
        vals = dict(zip(order, odds))
        base.update(dc_1x=vals['1x'], dc_12=vals['12'], dc_x2=vals['x2'],
                    dc_positions={lab: pos for pos, lab in enumerate(order)})
    else:
        base.update(home_odds=odds[0], draw_odds=odds[1], away_odds=odds[2])
    return base

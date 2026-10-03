"""
Odds provider module for BetPawa
Fetches odds using Selenium and populates the betslip (never places the bet).
"""
import logging
import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import Config
from fixture_parser import parse_fixtures_from_text

logger = logging.getLogger(__name__)

# Text that means we were served a block/challenge page, not the odds page
BLOCK_MARKERS = (
    'access denied', 'verify you are human', 'checking your browser',
    'attention required', 'unusual traffic', 'not available in your',
    'request blocked', 'captcha',
)

# JS: return the odds buttons (leaf nodes like "1.45") inside the smallest element
# that contains BOTH team names. Scoping to the row prevents clicking another
# match that happens to have the same odds.
FIND_ROW_ODDS_JS = """
const home = arguments[0].toLowerCase(), away = arguments[1].toLowerCase();
const oddsRe = /^\\d{1,3}\\.\\d{2}$/;
const all = Array.from(document.querySelectorAll('body *'));
const leaves = all.filter(e => e.children.length === 0 && (e.textContent || '').trim().length > 1);
const homeEls = leaves.filter(e => e.textContent.trim().toLowerCase() === home);
for (const h of homeEls) {
  let node = h;
  for (let depth = 0; depth < 8 && node.parentElement; depth++) {
    node = node.parentElement;
    const txt = (node.innerText || '').toLowerCase();
    if (!txt.includes(away)) continue;
    const odds = Array.from(node.querySelectorAll('*')).filter(
      e => e.children.length === 0 && oddsRe.test((e.textContent || '').trim()));
    if (odds.length >= 3 && odds.length <= 6) return odds;   // one row: 1 / X / 2 (+ maybe extras)
    if (odds.length > 6) break;                              // climbed into a multi-event container
  }
}
return [];
"""

# JS: locate the element that actually scrolls the match list. Modern SPAs usually scroll an
# inner container, so window.scrollBy() does nothing. We pick the scrollable element that
# holds the most odds values (falls back to the window).
FIND_SCROLLER_JS = """
function findScroller() {
  const cached = window.__betScroller;
  if (cached && document.contains(cached)) return cached;
  const re = /^\\d{1,3}\\.\\d{2}$/;
  let best = null, bestN = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (el.clientHeight < 200 || el.scrollHeight <= el.clientHeight + 50) continue;
    const oy = getComputedStyle(el).overflowY;
    if (oy !== 'auto' && oy !== 'scroll' && oy !== 'overlay') continue;
    let n = 0;
    for (const c of el.querySelectorAll('*')) {
      if (c.children.length === 0 && re.test((c.textContent || '').trim())) n++;
    }
    if (n > bestN) { best = el; bestN = n; }
  }
  window.__betScroller = best;
  return best;
}
"""

# JS: current scroll height of the list container (or the page)
HEIGHT_JS = FIND_SCROLLER_JS + """
const sc = findScroller() || document.scrollingElement || document.body;
return sc.scrollHeight;
"""

# JS: scroll one step in the container AND the window; True when at the bottom
SCROLL_STEP_JS = FIND_SCROLLER_JS + """
const sc = findScroller();
if (sc) sc.scrollBy(0, Math.floor(sc.clientHeight * 0.85));
window.scrollBy(0, Math.floor(window.innerHeight * 0.85));
const el = sc || document.scrollingElement || document.body;
return (el.scrollTop + el.clientHeight) >= (el.scrollHeight - 5);
"""

# JS: second attempt when nothing loaded - bring the last match into view (triggers
# infinite-scroll sentinels) and press any "load more" button
NUDGE_JS = """
const re = /^\\d{1,3}\\.\\d{2}$/;
const leaves = Array.from(document.querySelectorAll('body *')).filter(
  e => e.children.length === 0 && re.test((e.textContent || '').trim()));
if (leaves.length) leaves[leaves.length - 1].scrollIntoView({block: 'end'});
const more = Array.from(document.querySelectorAll('button, a, [role=button]')).find(
  b => /^(load more|show more|more matches|view more)$/i.test((b.textContent || '').trim()));
if (more) more.click();
return leaves.length;
"""

# JS: scroll both the list container and the window back to the top
SCROLL_TOP_JS = FIND_SCROLLER_JS + """
const sc = findScroller();
if (sc) sc.scrollTop = 0;
window.scrollTo(0, 0);
"""

# JS: outcome label ('1x' / '12' / 'x2') a price button carries in its own attributes, if any
BUTTON_LABEL_JS = """
const re = /(?:^|[^a-z0-9])(1x|12|x2)(?:[^a-z0-9]|$)/i;
let node = arguments[0];
for (let d = 0; d < 3 && node; d++, node = node.parentElement) {
  const attrs = [node.getAttribute('aria-label'), node.getAttribute('title'),
                 node.getAttribute('data-testid'), node.getAttribute('data-outcome'),
                 node.getAttribute('name')].filter(Boolean).join(' ');
  const m = attrs.match(re);
  if (m) return m[1].toLowerCase();
}
return null;
"""

CONSENT_BUTTON_TEXTS = ('accept', 'agree', 'i am 18', "i'm 18", 'got it', 'continue', 'ok')


class OddsProvider:
    """Provides odds data from BetPawa using Selenium"""

    def __init__(self):
        self.driver = None
        self.wait = None

    # ------------------------------------------------------------------ driver
    def _setup_driver(self, headless=None, keep_open=False):
        """Create a Chrome driver. Uses the browser's real user-agent (a hard-coded,
        outdated UA on a newer Chrome is itself a bot signal)."""
        headless = Config.HEADLESS if headless is None else headless
        opts = Options()
        if headless:
            opts.add_argument('--headless=new')
            opts.add_argument('--window-size=1400,1000')
        else:
            opts.add_argument('--start-maximized')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-notifications')
        opts.add_argument('--lang=en-US')
        if keep_open:
            opts.add_experimental_option('detach', True)   # Chrome stays open after Python exits

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.wait = WebDriverWait(self.driver, 40)

    # ------------------------------------------------------------- page helpers
    def _body_text(self):
        return self.driver.execute_script("return document.body ? document.body.innerText : ''") or ''

    def _dismiss_overlays(self):
        """Click through cookie / age-confirmation banners if present."""
        try:
            for btn in self.driver.find_elements(By.XPATH, "//button | //*[@role='button']"):
                label = (btn.text or '').strip().lower()
                if label and any(label == t or label.startswith(t) for t in CONSENT_BUTTON_TEXTS):
                    if btn.is_displayed():
                        self._safe_click(btn)
                        logger.info(f"Dismissed overlay button: '{label}'")
                        time.sleep(1)
                        break
        except Exception as e:
            logger.debug(f"Overlay dismissal skipped: {e}")

    def _wait_for_odds(self, timeout=40):
        """Wait until the SPA has rendered at least one fixture (not a fixed sleep)."""
        end = time.time() + timeout
        while time.time() < end:
            if parse_fixtures_from_text(self._body_text()):
                return True
            self._dismiss_overlays()
            time.sleep(2)
        return False

    def _save_debug_artifacts(self, tag):
        """Dump screenshot, page text and HTML so failures can be diagnosed."""
        try:
            os.makedirs(Config.DEBUG_DIR, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base = os.path.join(Config.DEBUG_DIR, f'{stamp}_{tag}')
            self.driver.save_screenshot(base + '.png')
            with open(base + '.txt', 'w', encoding='utf-8') as f:
                f.write(self._body_text())
            with open(base + '.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Saved debug files: {base}.png / .txt / .html")
        except Exception as e:
            logger.debug(f"Could not save debug artifacts: {e}")

    def _merge_visible_fixtures(self, merged, seen):
        """Parse what is currently rendered and add unseen fixtures. Returns count added."""
        added = 0
        for fx in parse_fixtures_from_text(self._body_text()):
            key = (fx['home_team'].lower(), fx['away_team'].lower())
            if key not in seen:
                seen.add(key)
                merged.append(fx)
                added += 1
        return added

    def _wait_for_growth(self, merged, seen, height_before, seconds):
        """Poll until new fixtures appear or the list grows taller. True if it did."""
        deadline = time.time() + seconds
        got_new = False
        while time.time() < deadline:
            time.sleep(0.5)
            if self._merge_visible_fixtures(merged, seen):
                got_new = True
            if got_new or self.driver.execute_script(HEIGHT_JS) > height_before:
                time.sleep(1.0)   # let the batch finish rendering, then capture it
                self._merge_visible_fixtures(merged, seen)
                return True
        return False

    def _scroll_and_wait_for_more(self, merged, seen):
        """Scroll one step (list container + window), wait up to SCROLL_LOAD_WAIT seconds for
        the next batch; if nothing arrives, nudge (last row into view / 'load more') and wait
        once more. Returns True if anything new appeared."""
        height_before = self.driver.execute_script(HEIGHT_JS)
        self.driver.execute_script(SCROLL_STEP_JS)
        if self._wait_for_growth(merged, seen, height_before, Config.SCROLL_LOAD_WAIT):
            logger.debug(f"Scroll loaded more (height was {height_before})")
            return True
        self.driver.execute_script(NUDGE_JS)
        grew = self._wait_for_growth(merged, seen, height_before, Config.SCROLL_LOAD_WAIT)
        logger.info(f"Scroll step: nothing after first wait; nudge {'loaded more' if grew else 'found nothing new'} "
                    f"(height {height_before})")
        return grew

    def _collect_fixtures_while_scrolling(self):
        """BetPawa lazy-loads more matches a few seconds after each scroll and
        virtualises long lists, so collect at every step and keep scrolling until
        several consecutive waits bring nothing new."""
        merged, seen = [], set()
        self.driver.execute_script(SCROLL_TOP_JS)
        time.sleep(1)
        self._merge_visible_fixtures(merged, seen)

        stalls = 0
        for step in range(Config.SCROLL_MAX_STEPS):
            if self._scroll_and_wait_for_more(merged, seen):
                stalls = 0
            else:
                stalls += 1
                if stalls >= Config.SCROLL_MAX_STALLS:
                    break
            if step % 5 == 0:
                logger.info(f"Scroll step {step + 1}: {len(merged)} fixtures so far")
            if len(merged) >= Config.MAX_FIXTURES:
                logger.info(f"Reached MAX_FIXTURES ({Config.MAX_FIXTURES}), stopping scroll")
                break

        logger.info(f"Scrolling finished with {len(merged)} fixtures")
        return merged

    # ------------------------------------------------------------------- fetch
    def fetch_odds_from_betpawa(self, market_type='1X2', sport='football'):
        """Fetch upcoming fixtures with 1/X/2 odds. Read-only: no betting actions."""
        try:
            logger.info(f"Fetching odds from BetPawa for {market_type} market")
            self._setup_driver()
            url = self._get_betpawa_url(market_type, sport)

            for attempt in range(1, 4):
                logger.info(f"Attempt {attempt}: navigating to {url}")
                self.driver.get(url)
                time.sleep(3)
                self._dismiss_overlays()

                if not self._wait_for_odds(timeout=40):
                    text = self._body_text().lower()
                    if any(m in text for m in BLOCK_MARKERS):
                        logger.error("BetPawa served a block/challenge page. Not attempting to bypass it.")
                        self._save_debug_artifacts('blocked')
                        return []
                    logger.warning(f"Attempt {attempt}: no fixtures rendered")
                    self._save_debug_artifacts(f'empty_attempt{attempt}')
                    continue

                fixtures = self._collect_fixtures_while_scrolling()
                if fixtures:
                    logger.info(f"Extracted {len(fixtures)} fixtures from BetPawa")
                    return fixtures

            logger.error("Failed to extract fixtures after all retries (see debug/ folder)")
            return []
        except Exception as e:
            logger.error(f"Error fetching odds from BetPawa: {e}", exc_info=True)
            return []
        finally:
            self._cleanup()

    # ------------------------------------------------------- betslip population
    def populate_betslip_with_selections(self, selections, market_type='1X2'):
        """Open BetPawa in a visible browser and click each selection's odds button.
        The final 'Place Bet' click is always left to the user."""
        try:
            logger.info("Populating BetPawa betslip with selections")
            self._setup_driver(headless=False, keep_open=True)
            self.driver.get(self._get_betpawa_url(market_type, 'football'))
            self._wait_for_odds(timeout=40)
            self._dismiss_overlays()

            added, failed = 0, []
            for i, sel in enumerate(selections, 1):
                label = f"{sel['home_team']} vs {sel['away_team']} - {sel['selection']} @ {sel['odds']:.2f}"
                logger.info(f"Adding selection {i}/{len(selections)}: {label}")

                if sel['selection'] not in ('Home Win', 'Away Win', 'Draw'):
                    # 1X / X2 odds are computed, not shown on the 1X2 page
                    logger.warning(f"Add manually via Double Chance market: {label}")
                    failed.append(sel)
                    continue

                if self._click_odds_button(sel):
                    added += 1
                    time.sleep(1.5)
                else:
                    failed.append(sel)
                    logger.warning(f"Could not add: {label}")

            logger.info(f"Added {added}/{len(selections)} selections to betslip")
            for sel in failed:
                print(f"  ! Add manually: {sel['home_team']} vs {sel['away_team']} - {sel['selection']}")
            self._scroll_to_betslip()
            return added > 0
        except Exception as e:
            logger.error(f"Error populating betslip: {e}", exc_info=True)
            return False
        # Browser intentionally left open for the user's manual final step

    def _click_visible_row(self, selection):
        """Click the 1/X/2 button for this exact match IF its row is currently rendered."""
        if selection['selection'] == '12':
            logger.error("Refusing to add a '12' selection - only 1X and X2 are allowed")
            return False
        if selection['selection'] in ('1X', 'X2'):
            idx = selection.get('col_index', 0 if selection['selection'] == '1X' else 1)   # columns: 1X, X2, 12
        else:
            idx = {'Home Win': 0, 'Draw': 1, 'Away Win': 2}[selection['selection']]
        buttons = self.driver.execute_script(
            FIND_ROW_ODDS_JS, selection['home_team'], selection['away_team'])
        if not buttons or len(buttons) <= idx:
            return False
        if selection['selection'] in ('1X', 'X2'):
            # If the buttons carry their own outcome label (aria-label/title/data attr), trust that
            # over position; and never click a button labelled '12'.
            labels = [self.driver.execute_script(BUTTON_LABEL_JS, b) for b in buttons[:3]]
            want = selection['selection'].lower()
            if want in labels:
                idx = labels.index(want)
            elif labels[idx] == '12':
                logger.error(f"Button at column {idx} is labelled 12 - skipping "
                             f"{selection['home_team']} vs {selection['away_team']}")
                return False
        target = buttons[idx]
        shown = (target.text or '').strip()
        if not self._odds_match(shown, selection['odds'], tolerance=0.02):
            logger.warning(
                f"Odds changed for {selection['home_team']} vs {selection['away_team']}: "
                f"expected {selection['odds']:.2f}, page shows {shown}. Skipping to be safe.")
            return False
        before = self._body_text().lower().count(selection['home_team'].lower())
        if not self._safe_click(target):
            return False
        time.sleep(1)
        after = self._body_text().lower().count(selection['home_team'].lower())
        if after <= before:
            logger.warning("Clicked, but betslip did not visibly change - please verify manually")
        return True

    def _click_odds_button(self, selection):
        """Click a selection, scrolling (and waiting for lazy-loaded rows) until its row appears."""
        self.driver.execute_script(SCROLL_TOP_JS)
        time.sleep(0.5)
        probe_m, probe_s, stalls = [], set(), 0
        for _ in range(Config.SCROLL_MAX_STEPS):
            if self._click_visible_row(selection):
                return True
            if self._scroll_and_wait_for_more(probe_m, probe_s):
                stalls = 0
            else:
                stalls += 1
                if stalls >= Config.SCROLL_MAX_STALLS:
                    break
        return False

    # ------------------------------------------------- market switching
    # Finds the 'Double Chance' control: exact/starts-with text, aria-label or title
    FIND_MARKET_TAB_JS = """
    const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
    const want = norm(arguments[0]);
    const visible = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const hits = Array.from(document.querySelectorAll('body *')).filter(e => {
      if (!visible(e) || e.tagName === 'OPTION' || e.tagName === 'SCRIPT' || e.tagName === 'STYLE') return false;
      const t = norm(e.textContent);
      const label = norm(e.getAttribute('aria-label')) + ' ' + norm(e.getAttribute('title'));
      return t === want || (t.startsWith(want) && t.length <= want.length + 12) || label.includes(want);
    });
    hits.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
    return hits.length ? hits[0] : null;
    """

    # Candidate elements that might open a market dropdown (near the top of the page)
    FIND_MARKET_OPENERS_JS = """
    const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
    const visible = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top < 700; };
    const out = Array.from(document.querySelectorAll('body *')).filter(e => {
      if (!visible(e)) return false;
      const t = norm(e.textContent);
      if (!t || t.length > 40) return false;
      const cls = (e.className && e.className.toString ? e.className.toString() : '').toLowerCase();
      return /^(1x2|1 x 2|match result|full time result|markets?|select market|all markets)/.test(t)
          || e.getAttribute('aria-haspopup') || e.getAttribute('role') === 'combobox'
          || e.getAttribute('aria-expanded') !== null
          || /(select|dropdown|market)/.test(cls);
    });
    out.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top
                       || a.querySelectorAll('*').length - b.querySelectorAll('*').length);
    return out.slice(0, 8);
    """

    # Short texts of clickable things near the top of the page, for diagnostics
    MENU_CANDIDATES_JS = """
    const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.top < 900; };
    return Array.from(document.querySelectorAll('button, a, [role=tab], [role=button], [role=option], select, li'))
      .filter(vis).map(e => (e.tagName + ' | ' + (e.textContent || '').replace(/\\s+/g, ' ').trim()).slice(0, 80))
      .filter((v, i, arr) => arr.indexOf(v) === i).slice(0, 120);
    """

    # marketId values to try if clicking fails (first one that visibly changes the odds wins)
    DC_URL_MARKET_IDS = ['_DC', 'DC', '_DOUBLE_CHANCE', 'DOUBLE_CHANCE', '_DoubleChance', 'DoubleChance', '_1X_X2']

    def _odds_snapshot(self, market='1X2'):
        """{(home, away): odds triple} for what is currently rendered."""
        snap = {}
        for fx in parse_fixtures_from_text(self._body_text(), market):
            key = (fx['home_team'].lower(), fx['away_team'].lower())
            snap[key] = (fx['home_odds'], fx['draw_odds'], fx['away_odds']) if market == '1X2' \
                else (fx['dc_1x'], fx['dc_12'], fx['dc_x2'])
        return snap

    @staticmethod
    def _rows_look_like_dc(snapshot):
        """Most rows must pass the sum(1/odds) ~ 2 test (a 1X2 page sums to ~1.1)."""
        rows = list(snapshot.values())
        good = sum(1 for o in rows if all(o) and 1.6 <= sum(1.0 / x for x in o) <= 2.7)
        return bool(rows) and good / len(rows) >= 0.8

    def _is_double_chance_page(self, before_1x2):
        """True if the same matches now show different odds, or 1X / X2 column labels appear."""
        lines = {ln.strip().lower() for ln in self._body_text().split('\n')}
        now = self._odds_snapshot('DC')
        if not now or not self._rows_look_like_dc(now):
            return False
        changed = any(k in before_1x2 and before_1x2[k] != v for k, v in now.items())
        return changed or {'1x', 'x2'} <= lines

    def _wait_for_double_chance(self, before_1x2, seconds=20, trust_url=False):
        """Wait for the Double Chance page. With trust_url (an address we know is the DC page),
        accept any rendered list whose odds are not identical to the 1X2 page's for the same match."""
        end = time.time() + seconds
        while time.time() < end:
            time.sleep(1.5)
            if self._is_double_chance_page(before_1x2):
                return True
            if trust_url:
                now = self._odds_snapshot('DC')
                if now and self._rows_look_like_dc(now) and \
                        not any(k in before_1x2 and before_1x2[k] == v for k, v in now.items()):
                    return True
        return False

    def _click_double_chance_control(self):
        """Try: visible tab -> <select> option -> open each candidate dropdown then pick it."""
        self.driver.execute_script(SCROLL_TOP_JS)
        time.sleep(0.8)

        tab = self.driver.execute_script(self.FIND_MARKET_TAB_JS, 'Double Chance')
        if tab is not None and self._safe_click(tab):
            logger.info("Clicked a visible 'Double Chance' control")
            return True

        # native <select>
        try:
            for sel in self.driver.find_elements(By.TAG_NAME, 'select'):
                for opt in sel.find_elements(By.TAG_NAME, 'option'):
                    if 'double chance' in (opt.text or '').lower():
                        Select(sel).select_by_visible_text(opt.text)
                        logger.info("Chose 'Double Chance' in a <select>")
                        return True
        except Exception as e:
            logger.debug(f"<select> attempt failed: {e}")

        # open dropdown candidates one by one
        openers = self.driver.execute_script(self.FIND_MARKET_OPENERS_JS) or []
        logger.info(f"Trying {len(openers)} possible market dropdown(s)")
        for opener in openers:
            if not self._safe_click(opener):
                continue
            time.sleep(1.2)
            tab = self.driver.execute_script(self.FIND_MARKET_TAB_JS, 'Double Chance')
            if tab is not None and self._safe_click(tab):
                logger.info("Opened a dropdown and clicked 'Double Chance'")
                return True
            try:   # close whatever we opened before trying the next candidate
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
        return False

    def _dump_menu_candidates(self):
        try:
            os.makedirs(Config.DEBUG_DIR, exist_ok=True)
            items = self.driver.execute_script(self.MENU_CANDIDATES_JS) or []
            path = os.path.join(Config.DEBUG_DIR, datetime.now().strftime('%Y%m%d_%H%M%S') + '_menu_candidates.txt')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(items))
            logger.info(f"Saved clickable-element list: {path}")
        except Exception as e:
            logger.debug(f"Could not dump menu candidates: {e}")

    def _switch_to_double_chance(self, before_1x2):
        """Switch the SPA to the Double Chance market. Order of attempts:
        1. the Double Chance page address (Config.DC_MARKET_URL, default built from BETPAWA_URL)
        2. click the control (tab / <select> / dropdown) - in place, keeps the betslip
        3. try likely marketId URLs (only when the betslip is still empty, since a reload may reset it)
        Returns True/False."""
        if Config.DC_MARKET_URL:
            logger.info(f"Opening Double Chance page: {Config.DC_MARKET_URL}")
            self.driver.get(Config.DC_MARKET_URL)
            time.sleep(3)
            self._dismiss_overlays()
            if self._wait_for_double_chance(before_1x2, 30, trust_url=True):
                logger.info("Double Chance market is open")
                self.driver.execute_script("window.__betScroller = null;")
                return True
            logger.warning("Double Chance URL did not show Double Chance odds; trying to click the control")
            self._save_debug_artifacts('dc_url_unverified')

        if self._click_double_chance_control() and self._wait_for_double_chance(before_1x2, 25):
            logger.info("Switched to Double Chance market by clicking")
            self.driver.execute_script("window.__betScroller = null;")
            return True

        if getattr(self, '_betslip_has_legs', False):
            return False   # don't reload the page and risk clearing selections already added

        base = Config.BETPAWA_URL
        for mid in self.DC_URL_MARKET_IDS:
            url = f"{base}/upcoming?marketId={mid}&categoryId=2"
            logger.info(f"Trying Double Chance URL: {url}")
            self.driver.get(url)
            time.sleep(3)
            if self._wait_for_double_chance(before_1x2, 12):
                logger.info(f"Double Chance works with marketId={mid}. "
                            f"Set DC_MARKET_URL={url} in .env to skip the search next time.")
                self.driver.execute_script("window.__betScroller = None;".replace('None', 'null'))
                return True
        return False

    # ------------------------------------------------- live build (streaming)
    def _stream_phase(self, market, selector, target_odds, max_legs, result, on_added, added_keys, pace=True):
        """Scroll the current market and add each fitting match to the betslip immediately.
        Returns True when the payout target / leg cap is reached."""
        checked, probe_merged, probe_seen, stalls = set(), [], set(), 0
        valid_dc_rows = 0
        self.driver.execute_script(SCROLL_TOP_JS)
        time.sleep(1)

        for _ in range(Config.SCROLL_MAX_STEPS):
            for fx in parse_fixtures_from_text(self._body_text(), market):
                key = (fx['home_team'].lower(), fx['away_team'].lower())
                if key in checked:
                    continue
                checked.add(key)
                result['fixtures_checked'] = max(result['fixtures_checked'], len(checked))
                if key in added_keys:      # never two picks from the same match
                    continue

                if market == 'DC':
                    if selector.dc_row_is_valid(fx):
                        valid_dc_rows += 1
                    elif len(checked) >= 6 and valid_dc_rows == 0:
                        result['notes'].append(
                            "The page did not show real Double Chance prices (they look like Home/Draw/Away "
                            "prices), so nothing was added. No win picks are ever used in Double Chance mode. "
                            "Send me the newest debug/*.txt and .png.")
                        self._save_debug_artifacts('dc_prices_look_like_1x2')
                        return False

                sel = selector.best_selection(fx) if market == '1X2' else selector.best_dc_selection(fx)
                if not sel:
                    continue
                if market == 'DC' and sel['selection'] not in ('1X', 'X2'):
                    continue   # Double Chance mode: 1X and X2 only, never 12
                if pace and not self._meets_pace(sel, target_odds, result['combined_odds'],
                                                 max_legs - len(result['added']), selector.max_odds):
                    continue
                if not self._click_visible_row(sel):
                    logger.warning(f"Could not add {fx['home_team']} vs {fx['away_team']}")
                    continue

                added_keys.add(key)
                self._betslip_has_legs = True
                result['added'].append(sel)
                result['combined_odds'] *= sel['odds']
                if on_added:
                    on_added(sel, result['combined_odds'], len(checked))
                if result['combined_odds'] >= target_odds or len(result['added']) >= max_legs:
                    result['reached_target'] = result['combined_odds'] >= target_odds
                    result['stop_reason'] = 'target' if result['reached_target'] else 'cap'
                    return True

            if self._scroll_and_wait_for_more(probe_merged, probe_seen):
                stalls = 0
            else:
                stalls += 1
                if stalls >= Config.SCROLL_MAX_STALLS:
                    break

        logger.info(f"{market} phase finished: {len(checked)} matches checked, "
                    f"{len(result['added'])} legs in slip")
        return False

    @staticmethod
    def _meets_pace(sel, target_odds, combined, slots_left, max_odds, slack=0.98):
        """With a leg cap, the slip only reaches the target if the legs average at least
        r = (target / combined) ** (1 / slots_left). Skip legs priced clearly below r, so the
        limited slots are spent on the best-priced picks that still pass the probability floor.
        Not applied when r is above the maximum allowed odds (then nothing could keep pace)."""
        if slots_left <= 0 or combined >= target_odds:
            return True
        r = (target_odds / combined) ** (1.0 / slots_left)
        if r > max_odds:
            return True
        return sel['odds'] >= r * slack

    def build_betslip_live(self, selector, stake, min_payout, max_legs, on_added=None, pace=None):
        """One pass, no pre-scan: scroll BetPawa and click each fitting selection into the
        betslip the moment it appears; stop at the payout target (or leg cap).
        WIN -> 1X2 market; DOUBLE_CHANCE -> Double Chance market (real 1X / X2 prices);
        MIXED -> 1X2 first, then Double Chance for the remaining matches.
        Never clicks the final 'Place Bet' button and leaves the browser open.

        Returns dict: status ('ok'|'no_fixtures'|'blocked'|'error'), added, combined_odds,
        reached_target, fixtures_checked, notes.
        """
        pace = Config.LIVE_PACE if pace is None else pace
        result = {'status': 'ok', 'added': [], 'combined_odds': 1.0, 'stop_reason': 'exhausted',
                  'reached_target': False, 'fixtures_checked': 0, 'notes': []}
        self._betslip_has_legs = False
        try:
            self._setup_driver(headless=False, keep_open=True)   # visible: the user finishes the bet
            url = self._get_betpawa_url('1X2', 'football')
            logger.info(f"Live build: navigating to {url}")
            self.driver.get(url)
            time.sleep(3)
            self._dismiss_overlays()

            if not self._wait_for_odds(timeout=40):
                blocked = any(m in self._body_text().lower() for m in BLOCK_MARKERS)
                self._save_debug_artifacts('blocked' if blocked else 'empty_live')
                result['status'] = 'blocked' if blocked else 'no_fixtures'
                return result

            mt = selector.market_type
            phases = {Config.MARKET_WIN: ['1X2'],
                      Config.MARKET_DOUBLE_CHANCE: ['DC'],
                      Config.MARKET_MIXED: ['1X2', 'DC']}.get(mt, ['1X2'])
            target_odds = min_payout / stake
            added_keys = set()
            before_1x2 = self._odds_snapshot('1X2')

            for phase in phases:
                if phase == 'DC':
                    if not self._switch_to_double_chance(before_1x2):
                        self._save_debug_artifacts('double_chance_switch_failed')
                        self._dump_menu_candidates()
                        result['notes'].append(
                            "Could not open the Double Chance market automatically. Open it in the browser, "
                            "copy the page address into DC_MARKET_URL in .env - or send me the newest files in "
                            "debug/ (the .txt, the .png and *_menu_candidates.txt).")
                        break
                if self._stream_phase(phase, selector, target_odds, max_legs, result, on_added, added_keys, pace):
                    break

            self._save_debug_artifacts('live_end')
            self._scroll_to_betslip()
            return result
        except Exception as e:
            logger.error(f"Live build error: {e}", exc_info=True)
            result['status'] = 'error'
            return result
        # browser intentionally left open for the user's manual final step

    def _safe_click(self, element):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.4)
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e:
                logger.debug(f"Safe click failed: {e}")
                return False

    def _odds_match(self, odds_text, target_odds, tolerance=0.01):
        try:
            return abs(float(odds_text) - target_odds) <= tolerance
        except (TypeError, ValueError):
            return False

    def _scroll_to_betslip(self):
        try:
            els = self.driver.find_elements(
                By.XPATH, "//*[contains(translate(text(),'BETSLIP','betslip'),'betslip')]")
            if els:
                els[0].click()
                time.sleep(1)
        except Exception:
            pass

    def _get_betpawa_url(self, market_type, sport):
        base_url = Config.BETPAWA_URL
        if sport == 'basketball' and market_type == '1X2':
            return f"{base_url}/upcoming?marketId=ML&categoryId=3"
        return f"{base_url}/upcoming?marketId=_1X2&categoryId=2"

    def _cleanup(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # ------------------------------------------------------------ manual input
    def _get_custom_input(self):
        """Collect fixture data manually until the user enters 'done'."""
        fixtures = []

        print("Enter fixtures as: 'Home Team vs Away Team, Home Odds, Away Odds' or 'done' to finish.")

        while True:
            try:
                raw_input = input().strip()
            except EOFError:
                break

            if not raw_input:
                continue

            if raw_input.lower() == 'done':
                if fixtures:
                    break
                continue

            fixture = self._parse_manual_fixture(raw_input)
            if fixture:
                fixtures.append(fixture)
                print(f"Added fixture: {fixture['home_team']} vs {fixture['away_team']}")
            else:
                print("Invalid format. Use: 'Team A vs Team B, 1.45, 2.60'")

        return fixtures

    def _parse_manual_fixture(self, raw_input):
        """Parse a manual fixture line into a standard fixture dictionary."""
        try:
            import re

            match = re.match(r'^(.+?)\s+(?:vs|v)\s+(.+?)(?:\s*,\s*|\s+)(.+)$', raw_input, re.IGNORECASE)
            if not match:
                return None

            home_team = re.sub(r'\s+', ' ', match.group(1)).strip()
            away_team = re.sub(r'\s+', ' ', match.group(2)).strip()
            odds_part = match.group(3).strip()

            odds_values = re.findall(r'\d+(?:\.\d+)?', odds_part)
            if len(odds_values) < 2:
                return None

            numbers = [float(value) for value in odds_values[:3]]
            if len(numbers) == 2:
                home_odds, away_odds = numbers
                draw_odds = None
            else:
                home_odds, draw_odds, away_odds = numbers

            if not home_team or not away_team:
                return None

            return {
                'competition': 'Manual Input',
                'date_time': 'TBD',
                'home_team': home_team,
                'away_team': away_team,
                'home_odds': home_odds,
                'draw_odds': draw_odds,
                'away_odds': away_odds,
            }
        except Exception:
            return None

    def get_manual_odds_input(self):
        """Prompt the user for manual fixture input as a fallback."""
        return self._get_custom_input()

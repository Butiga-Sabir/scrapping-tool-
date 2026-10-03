"""
Launches the user's installed Google Chrome as an independent process and lets Selenium attach to it.

Why: a Chrome window started by Selenium dies when Python exits and starts with an empty profile.
A separately launched Chrome (with a dedicated profile folder) stays open after the script ends,
remembers your BetPawa login, and is reused on the next run.
"""
import logging
import os
import shutil
import subprocess
import time
import urllib.request

logger = logging.getLogger(__name__)

WINDOWS_CANDIDATES = [
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
]
MAC_CANDIDATES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
LINUX_NAMES = ("google-chrome", "google-chrome-stable", "chrome")


def find_chrome(explicit=None):
    """Path to Google Chrome, or None. `explicit` (CHROME_PATH) wins if it exists."""
    if explicit and os.path.isfile(explicit):
        return explicit
    for candidate in WINDOWS_CANDIDATES + MAC_CANDIDATES:
        path = os.path.expandvars(candidate)
        if os.path.isfile(path):
            return path
    for name in LINUX_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def debug_port_open(port, timeout=1.0):
    """True if a Chrome with this remote-debugging port is already running."""
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=timeout).read()
        return True
    except Exception:
        return False


def build_command(chrome, port, profile_dir):
    return [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",   # dedicated profile: keeps login, never touches your main one
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-notifications",
        "--lang=en-US",
    ]


def ensure_chrome(port, profile_dir, chrome_path=None, wait_seconds=25):
    """Make sure a debuggable Chrome is running. Returns 'reused' or 'launched'.
    Raises RuntimeError if Chrome can't be found or doesn't start."""
    if debug_port_open(port):
        return "reused"

    chrome = find_chrome(chrome_path)
    if not chrome:
        raise RuntimeError("Google Chrome was not found. Set CHROME_PATH in .env to chrome.exe.")

    os.makedirs(profile_dir, exist_ok=True)
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    logger.info(f"Launching Chrome: {chrome} (profile: {profile_dir}, port {port})")
    subprocess.Popen(build_command(chrome, port, profile_dir),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, **kwargs)

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if debug_port_open(port):
            return "launched"
        time.sleep(0.5)
    raise RuntimeError(f"Chrome started but port {port} never opened "
                       "(is another Chrome using the same profile folder?)")

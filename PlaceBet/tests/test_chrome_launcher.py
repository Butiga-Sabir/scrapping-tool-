import unittest
from unittest import mock

import chrome_launcher as cl


class ChromeLauncherTests(unittest.TestCase):
    def test_explicit_path_wins_when_file_exists(self):
        with mock.patch('os.path.isfile', side_effect=lambda p: p == r'C:\x\chrome.exe'):
            self.assertEqual(cl.find_chrome(r'C:\x\chrome.exe'), r'C:\x\chrome.exe')

    def test_returns_none_when_chrome_not_installed(self):
        with mock.patch('os.path.isfile', return_value=False), mock.patch('shutil.which', return_value=None):
            self.assertIsNone(cl.find_chrome())

    def test_command_has_dedicated_profile_and_debug_port(self):
        cmd = cl.build_command('chrome.exe', 9222, 'D:/prof')
        self.assertIn('--remote-debugging-port=9222', cmd)
        self.assertIn('--user-data-dir=D:/prof', cmd)
        self.assertNotIn('--headless', ' '.join(cmd))

    def test_reuses_running_chrome_without_launching(self):
        with mock.patch.object(cl, 'debug_port_open', return_value=True), \
             mock.patch('subprocess.Popen') as popen:
            self.assertEqual(cl.ensure_chrome(9222, 'prof'), 'reused')
            popen.assert_not_called()

    def test_launches_then_waits_for_port(self):
        states = iter([False, False, True])
        with mock.patch.object(cl, 'debug_port_open', side_effect=lambda *_: next(states)), \
             mock.patch.object(cl, 'find_chrome', return_value='chrome.exe'), \
             mock.patch('os.makedirs'), mock.patch('time.sleep'), \
             mock.patch('subprocess.Popen') as popen:
            self.assertEqual(cl.ensure_chrome(9222, 'prof', wait_seconds=5), 'launched')
            popen.assert_called_once()

    def test_raises_clear_error_when_chrome_missing(self):
        with mock.patch.object(cl, 'debug_port_open', return_value=False), \
             mock.patch.object(cl, 'find_chrome', return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                cl.ensure_chrome(9222, 'prof')
            self.assertIn('CHROME_PATH', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()

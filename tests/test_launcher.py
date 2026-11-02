"""Start backendu: rzeczywisty proces Windows i jawne ścieżki awarii launchera."""
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import manage

class LauncherTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='win32','Native Windows process creation flags')
    def test_real_background_child_finishes_after_launcher_returns(self):
        with tempfile.TemporaryDirectory() as folder:
            marker=Path(folder)/'finished'
            code='import time;from pathlib import Path;time.sleep(.2);Path('+repr(str(marker))+').touch()'
            child=manage.launch_background([sys.executable,'-c',code],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:self.assertEqual(child.wait(timeout=5),0);self.assertTrue(marker.exists())
            finally:
                if child.poll() is None:child.kill();child.wait()
    @unittest.skipUnless(sys.platform=='win32','Native Windows constants')
    def test_access_denied_breakaway_falls_back_without_hiding_other_errors(self):
        denied=OSError('fixture');denied.winerror=5
        with patch.object(manage.subprocess,'Popen',side_effect=[denied,'process']) as launch:
            self.assertEqual(manage.launch_background(['fixture'],cwd='folder'),'process')
        first,second=launch.call_args_list
        self.assertTrue(first.kwargs['creationflags']&subprocess.CREATE_BREAKAWAY_FROM_JOB)
        self.assertEqual(second.kwargs['creationflags'],subprocess.CREATE_NO_WINDOW)
        self.assertEqual(second.kwargs['cwd'],'folder')
    @unittest.skipUnless(sys.platform=='win32','Native Windows launch failure')
    def test_missing_program_is_not_retried_as_permission_failure(self):
        missing=OSError('fixture');missing.winerror=2
        with patch.object(manage.subprocess,'Popen',side_effect=missing) as launch:
            with self.assertRaises(OSError):manage.launch_background(['missing'])
        self.assertEqual(launch.call_count,1)
    def test_non_windows_branch_uses_separate_session(self):
        with patch.object(manage,'sys',SimpleNamespace(platform='linux')),patch.object(manage.subprocess,'Popen',return_value='process') as launch:
            self.assertEqual(manage.launch_background(['fixture']),'process')
        self.assertTrue(launch.call_args.kwargs['start_new_session'])
        self.assertNotIn('creationflags',launch.call_args.kwargs)

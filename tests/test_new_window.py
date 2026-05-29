# -*- coding: utf-8 -*-

import os
import unittest


class TestNewWindowProcessConfig(unittest.TestCase):
    def test_sets_cwd_to_project_root_and_sets_pythonpath(self):
        from chemcanvas.main import build_new_window_process_config

        argv, cwd, env = build_new_window_process_config(
            sys_executable="/opt/homebrew/opt/python@3.14/bin/python3.14",
            existing_env={},
        )

        self.assertEqual(argv[:2], ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-m"])
        self.assertEqual(argv[2], "chemcanvas.main")
        self.assertTrue(os.path.isdir(cwd))
        self.assertTrue(env["PYTHONPATH"].startswith(cwd))

    def test_preserves_existing_pythonpath(self):
        from chemcanvas.main import build_new_window_process_config

        argv, cwd, env = build_new_window_process_config(
            sys_executable="python",
            existing_env={"PYTHONPATH": "/tmp/one:/tmp/two"},
        )

        self.assertEqual(argv, ["python", "-m", "chemcanvas.main"])
        self.assertTrue(env["PYTHONPATH"].startswith(cwd + os.pathsep))
        self.assertTrue(env["PYTHONPATH"].endswith("/tmp/one:/tmp/two"))


if __name__ == "__main__":
    unittest.main()

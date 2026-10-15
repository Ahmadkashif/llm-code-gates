import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import helpers as h
import gateslib as g

sys.path.insert(0, str(h.KIT))
import render  # noqa: E402


class RenderTests(unittest.TestCase):
    def test_check_ok(self):
        p = subprocess.run([sys.executable, str(h.KIT / "render.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_small_tier_guard_and_vram(self):
        j = g.load_yaml_file(h.KIT / "profiles/judges/local-8gb.yml")
        self.assertEqual(render.check_judge(j, 8), [])
        j2 = dict(j, verify=True, prompts=["find-security"])
        probs = render.check_judge(j2, 8)
        self.assertTrue(any("not reliable" in p for p in probs), probs)
        big = g.load_yaml_file(h.KIT / "profiles/judges/local-48gb-plus.yml")
        self.assertTrue(any("VRAM" in p for p in render.check_judge(big, 8)))
        self.assertTrue(any("require verify" in p for p in render.check_judge(dict(j, blocking_categories=["security"]), 8)))

    def test_render_writes_config(self):
        out = Path(tempfile.mkdtemp()) / ".gates"
        out.mkdir()
        (out / "site.env").write_text("GATES_LICENCE_OWNER=Example\nGATES_JUDGE_API_KEY=must-not-be-copied\n")
        p = subprocess.run([sys.executable, str(h.KIT / "render.py"), "--stack", "python", "--judge", "stub",
                            "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cfg = (out / "config.env").read_text()
        self.assertIn("GATES_LICENCE_OWNER=Example", cfg)
        self.assertNotIn("must-not-be-copied", cfg)
        self.assertIn("GATES_LAYER_FAST=test-tamper,dep-check,semgrep-changed,scope-check", cfg)


if __name__ == "__main__":
    unittest.main()

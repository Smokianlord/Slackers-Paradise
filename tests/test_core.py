import os
import tempfile
import time
import unittest
from pathlib import Path

from core.cleaner import execute_clean, scan_empty_folders
from core.folio import render_scan_data, scan_directory
from core.renamer import RenameEngine, natural_key


class RenamerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.engine = RenameEngine()

    def tearDown(self):
        self._tmp.cleanup()

    def touch(self, *names):
        for n in names:
            (self.dir / n).write_text(n)

    def test_natural_order(self):
        self.assertEqual(sorted(["f10", "f2", "f1"], key=natural_key), ["f1", "f2", "f10"])

    def test_sequential_uses_natural_order(self):
        self.touch("p10.txt", "p2.txt", "p1.txt")
        plan = self.engine.generate_plan(self.dir, mode="sequential", seq_prefix="N_", seq_padding=2)
        self.assertEqual([i["new_name"] for i in plan["items"]], ["N_01.txt", "N_02.txt", "N_03.txt"])
        self.assertEqual([i["old_name"] for i in plan["items"]], ["p1.txt", "p2.txt", "p10.txt"])

    def test_invalid_character_blocked(self):
        self.touch("a.txt")
        plan = self.engine.generate_plan(self.dir, mode="find_replace", find_text="a", replace_text="a:b")
        self.assertEqual(plan["items"][0]["status"], "invalid")
        self.assertEqual(plan["ready"], 0)

    def test_conflict_with_unselected_file(self):
        self.touch("a.txt", "b.png")
        plan = self.engine.generate_plan(self.dir, mode="find_replace", find_text="a", replace_text="b",
                                         extension_filter=".txt")
        self.assertEqual(plan["items"][0]["status"], "ready")  # b.txt does not exist
        self.touch("b.txt")
        plan = self.engine.generate_plan(self.dir, mode="find_replace", find_text="a", replace_text="b",
                                         extension_filter="a.txt")
        # only a.txt matches the filter? "a.txt" is not an extension -> nothing selected
        self.assertEqual(plan["total"], 0)

    def test_chain_rename_and_undo(self):
        # 1.txt -> 2.txt while 2.txt -> 3.txt: needs the two-phase logic
        self.touch("1.txt", "2.txt")
        pairs = [(self.dir / "2.txt", self.dir / "3.txt"), (self.dir / "1.txt", self.dir / "2.txt")]
        done, failed = RenameEngine._two_phase(pairs)
        self.assertEqual(failed, [])
        self.assertEqual((self.dir / "2.txt").read_text(), "1.txt")
        self.assertEqual((self.dir / "3.txt").read_text(), "2.txt")
        self.engine.undo_stack.append([(dst, src) for src, dst in done])
        res = self.engine.undo_last_rename()
        self.assertEqual(res["restored"], 2)
        self.assertEqual((self.dir / "1.txt").read_text(), "1.txt")
        self.assertEqual((self.dir / "2.txt").read_text(), "2.txt")

    def test_regex_and_case_insensitive(self):
        self.touch("Photo_A.jpg")
        plan = self.engine.generate_plan(self.dir, mode="find_replace", find_text="photo", replace_text="Img",
                                         case_sensitive=False)
        self.assertEqual(plan["items"][0]["new_name"], "Img_A.jpg")
        plan = self.engine.generate_plan(self.dir, mode="find_replace", find_text=r"_(\w)", replace_text=r"-\1",
                                         use_regex=True)
        self.assertEqual(plan["items"][0]["new_name"], "Photo-A.jpg")


class CleanerTests(unittest.TestCase):
    def test_nested_empty_folders_reported_once_at_top(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "work"
            (root / "a" / "b" / "c").mkdir(parents=True)
            (root / "keep").mkdir()
            (root / "keep" / "file.txt").write_text("x")
            (root / "keep" / "empty").mkdir()
            found = {Path(i["path"]).relative_to(root).as_posix() for i in scan_empty_folders(root)}
            self.assertEqual(found, {"a", "keep/empty"})

    def test_execute_clean_permanent(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "junk.tmp"
            f.write_text("junk")
            res = execute_clean([{"path": f, "category": "Temp file", "is_dir": False, "size_bytes": 4, "selected": True}])
            self.assertEqual(res["cleaned"], 1)
            self.assertFalse(f.exists())


class FolioTests(unittest.TestCase):
    def test_tree_respects_scan_and_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            (root / "sub" / "a.txt").write_text("hello")
            (root / "b.png").write_text("x")
            scan = scan_directory(root, recursive=True, patterns=["*.txt"])
            tree = render_scan_data(scan, "tree")
            self.assertIn("a.txt", tree)
            self.assertNotIn("b.png", tree)
            self.assertIn("Name,Relative Path", render_scan_data(scan, "csv"))
            self.assertIn('"files": 1', render_scan_data(scan, "json"))


if __name__ == "__main__":
    unittest.main()

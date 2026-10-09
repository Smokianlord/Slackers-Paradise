import tempfile
import unittest
from pathlib import Path

from core.builder import (
    apply_suggestions, execute_create_folders, expand_sequence, parse_folder_names,
    preview_creation, undo_created_folders, SequenceTooLarge,
)
from core.naming import analyze_name

TITLE_COLON = "Battle Through the Heaven: Choose Three Out of Five Cheats, a Perfect Start!"
TITLE_QUESTION = "Global Lottery: I Pull All Gold, Yet You Call My Summoner Weak?"


class ParsingTests(unittest.TestCase):
    def test_commas_are_part_of_the_name(self):
        names = parse_folder_names(f"{TITLE_COLON}\nPlain, With Comma")
        self.assertEqual(names, [TITLE_COLON, "Plain, With Comma"])

    def test_one_folder_per_line_and_blank_lines_ignored(self):
        self.assertEqual(parse_folder_names("a\n\n  \nb\n"), ["a", "b"])

    def test_duplicates_removed_case_insensitively(self):
        self.assertEqual(parse_folder_names("Docs\ndocs\nDOCS"), ["Docs"])

    def test_sequences(self):
        self.assertEqual(expand_sequence("E_{08..10}"), ["E_08", "E_09", "E_10"])
        self.assertEqual(expand_sequence("P_{A..C}"), ["P_A", "P_B", "P_C"])
        self.assertEqual(expand_sequence("S_{3..1}"), ["S_3", "S_2", "S_1"])

    def test_huge_sequence_rejected(self):
        with self.assertRaises(SequenceTooLarge):
            expand_sequence("x_{1..999999}")

    def test_wrapping_quotes_stripped_but_inner_kept(self):
        self.assertEqual(parse_folder_names('"My Folder"'), ["My Folder"])


class SuggestionTests(unittest.TestCase):
    def test_colon_title(self):
        issues, fix = analyze_name(TITLE_COLON, nested=False)
        self.assertTrue(issues)
        self.assertEqual(fix, "Battle Through the Heaven - Choose Three Out of Five Cheats, a Perfect Start!")

    def test_question_mark_title(self):
        issues, fix = analyze_name(TITLE_QUESTION, nested=False)
        self.assertTrue(issues)
        self.assertEqual(fix, "Global Lottery - I Pull All Gold, Yet You Call My Summoner Weak")

    def test_valid_name_has_no_issues(self):
        issues, fix = analyze_name("Plain, Name (2024)", nested=False)
        self.assertEqual(issues, [])
        self.assertEqual(fix, "Plain, Name (2024)")

    def test_reserved_trailing_and_slash_cases(self):
        self.assertEqual(analyze_name("CON", nested=False)[1], "CON_")
        self.assertEqual(analyze_name("Notes. ", nested=False)[1], "Notes")
        self.assertEqual(analyze_name("Fate/Zero", nested=False)[1], "Fate-Zero")
        self.assertEqual(analyze_name('He said "hi"', nested=False)[1], "He said 'hi'")

    def test_unfixable(self):
        issues, fix = analyze_name("???", nested=False)
        self.assertTrue(issues)
        self.assertEqual(fix, "")

    def test_nested_paths_keep_structure(self):
        issues, fix = analyze_name("src/Bad: Name/ui", nested=True)
        self.assertEqual(fix, "src/Bad - Name/ui")


class PreviewAndCreateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_preview_flags_fixable_and_valid(self):
        raw = f"{TITLE_COLON}\nGood, Name\n{TITLE_QUESTION}"
        pv = preview_creation(self.base, raw, nested=False)
        self.assertEqual([i["status"] for i in pv["items"]], ["fixable", "new", "fixable"])
        self.assertEqual(pv["fixable"], 2)

    def test_create_skips_problem_names_unless_fixes_applied(self):
        raw = f"Good, Name\n{TITLE_COLON}"
        res = execute_create_folders(self.base, raw, nested=False)
        self.assertEqual(res["created"], ["Good, Name"])
        self.assertEqual(len(res["failed"]), 1)
        self.assertEqual([p.name for p in self.base.iterdir()], ["Good, Name"])

    def test_create_with_fixes(self):
        res = execute_create_folders(self.base, f"{TITLE_QUESTION}", nested=False, apply_fixes=True)
        self.assertEqual(res["created"], ["Global Lottery - I Pull All Gold, Yet You Call My Summoner Weak"])
        self.assertTrue((self.base / res["created"][0]).is_dir())

    def test_fix_collision_is_flagged_duplicate(self):
        pv = preview_creation(self.base, "A: B\nA - B", nested=False, apply_fixes=True)
        self.assertEqual([i["status"] for i in pv["items"]], ["new", "duplicate"])

    def test_existing_detected(self):
        (self.base / "src").mkdir()
        pv = preview_creation(self.base, "src\nlib")
        self.assertEqual([i["status"] for i in pv["items"]], ["existing", "new"])

    def test_nested_creation_and_undo(self):
        res = execute_create_folders(self.base, "a/b/c\nx")
        self.assertEqual(len(res["created_dirs"]), 4)  # a, a/b, a/b/c, x
        (self.base / "a" / "b" / "c" / "keep.txt").write_text("hi")
        undo = undo_created_folders(res["created_dirs"])
        self.assertTrue((self.base / "a" / "b" / "c" / "keep.txt").exists())  # non-empty is never removed
        self.assertFalse((self.base / "x").exists())
        self.assertEqual(undo["removed"], 1)

    def test_apply_suggestions_rewrites_text(self):
        text, changed = apply_suggestions(f"ok\n{TITLE_QUESTION}", nested=False)
        self.assertEqual(changed, 1)
        self.assertEqual(text.splitlines()[1], "Global Lottery - I Pull All Gold, Yet You Call My Summoner Weak")


if __name__ == "__main__":
    unittest.main()

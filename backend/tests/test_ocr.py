import unittest
from pathlib import Path

from app.services.documents import _ocr_command_args


class OcrCommandTests(unittest.TestCase):
    def test_command_template_replaces_path_and_language(self):
        args = _ocr_command_args("tesseract {path} stdout -l {language}", Path("paper.pdf"), "eng")

        self.assertEqual(args, ["tesseract", "paper.pdf", "stdout", "-l", "eng"])

    def test_command_without_path_appends_source_path(self):
        args = _ocr_command_args("custom-ocr --stdout", Path("scan.pdf"), "eng")

        self.assertEqual(args, ["custom-ocr", "--stdout", "scan.pdf"])


if __name__ == "__main__":
    unittest.main()

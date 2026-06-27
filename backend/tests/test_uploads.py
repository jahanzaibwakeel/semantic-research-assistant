import io
import unittest

from fastapi import HTTPException, UploadFile

from app.services.uploads import persist_pdf_upload


def make_upload(name: str, content_type: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data), headers={"content-type": content_type})


class UploadValidationTests(unittest.TestCase):
    def test_valid_pdf_is_written(self):
        with tempfile_directory() as tmp_path:
            target = tmp_path / "paper.pdf"
            checksum = persist_pdf_upload(make_upload("paper.pdf", "application/pdf", b"%PDF-1.7\nbody"), target, 1)

            self.assertEqual(target.read_bytes(), b"%PDF-1.7\nbody")
            self.assertEqual(len(checksum), 64)

    def test_non_pdf_magic_is_rejected(self):
        with tempfile_directory() as tmp_path:
            with self.assertRaises(HTTPException) as exc:
                persist_pdf_upload(make_upload("paper.pdf", "application/pdf", b"not a pdf"), tmp_path / "paper.pdf", 1)

            self.assertEqual(exc.exception.status_code, 400)

    def test_oversized_pdf_is_rejected_and_removed(self):
        with tempfile_directory() as tmp_path:
            target = tmp_path / "large.pdf"
            with self.assertRaises(HTTPException) as exc:
                persist_pdf_upload(make_upload("large.pdf", "application/pdf", b"%PDF-" + (b"x" * 20)), target, 0)

            self.assertEqual(exc.exception.status_code, 413)
            self.assertFalse(target.exists())


class tempfile_directory:
    def __enter__(self):
        import tempfile
        from pathlib import Path

        self._directory = tempfile.TemporaryDirectory()
        return Path(self._directory.__enter__())

    def __exit__(self, exc_type, exc, tb):
        return self._directory.__exit__(exc_type, exc, tb)


if __name__ == "__main__":
    unittest.main()

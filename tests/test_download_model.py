from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from download_model import EXPECTED_SHA256, file_sha256


class DownloadModelTests(unittest.TestCase):
    def test_file_sha256(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            path.write_bytes(b"test model")
            self.assertEqual(
                file_sha256(path),
                "e6a8036e9cb9f8c9f52ffd985c4d6f04"
                "98d94e6919f4c67b6423da0176e549fa",
            )

    def test_expected_checksum_shape(self) -> None:
        self.assertEqual(len(EXPECTED_SHA256), 64)
        int(EXPECTED_SHA256, 16)


if __name__ == "__main__":
    unittest.main()

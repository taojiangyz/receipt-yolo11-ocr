from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen


MODEL_URL = (
    "https://github.com/taojiangyz/receipt-yolo11-ocr/"
    "releases/download/v1.0.0/best.pt"
)
MODEL_PATH = Path("models/best.pt")
EXPECTED_SHA256 = (
    "917538afaa7fb48d12aeb6f30df0021"
    "bfaec51cafbaf4e71203ba1660eb381f6"
)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if MODEL_PATH.exists() and file_sha256(MODEL_PATH) == EXPECTED_SHA256:
        print(f"Model already verified: {MODEL_PATH}")
        return

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = MODEL_PATH.with_suffix(".pt.download")
    print(f"Downloading model from {MODEL_URL}")

    try:
        with urlopen(MODEL_URL, timeout=120) as response:
            with temporary_path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)

        actual_hash = file_sha256(temporary_path)
        if actual_hash != EXPECTED_SHA256:
            raise RuntimeError(
                f"Model checksum mismatch: expected {EXPECTED_SHA256}, "
                f"received {actual_hash}"
            )
        temporary_path.replace(MODEL_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f"Verified model: {MODEL_PATH}")


if __name__ == "__main__":
    main()

from pathlib import Path
import shutil

SOURCE_ROOT = Path("data/raw_images_original")
TARGET_ROOT = Path("data/raw_images")

STORE_PREFIXES = {
    "seven": "seven",
    "family": "family",
    "lawson": "lawson",
    "mybasket": "mybasket",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic"}

ANGLES = ["a", "b", "c"]  # 每张小票3张照片


def main():
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)

    for store_folder, prefix in STORE_PREFIXES.items():
        folder = SOURCE_ROOT / store_folder

        if not folder.exists():
            print(f"Skip: {folder} does not exist")
            continue

        images = sorted(
            [
                p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS
            ]
        )

        if not images:
            print(f"No images found in {folder}")
            continue

        print(f"\nStore: {store_folder}")
        print(f"Images: {len(images)}")

        for idx, img_path in enumerate(images):
            receipt_id = idx // 3 + 1
            angle = ANGLES[idx % 3]

            new_name = f"{prefix}_{receipt_id:03d}_{angle}{img_path.suffix.lower()}"
            target_path = TARGET_ROOT / new_name

            shutil.copy2(img_path, target_path)
            print(f"{img_path.name} -> {new_name}")

    print("\nDone. Renamed images are saved in data/raw_images")


if __name__ == "__main__":
    main()

from pathlib import Path
import random
import shutil
from collections import defaultdict, Counter

SRC_IMAGE_DIR = Path("data/yolo_all/images")
SRC_LABEL_DIR = Path("data/yolo_all/labels")
OUT_DIR = Path("data/yolo_receipt")

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

random.seed(42)

# train / val / test 比例
TRAIN_RATIO = 0.7
VAL_RATIO = 0.15
TEST_RATIO = 0.15


def get_receipt_id(stem: str) -> str:
    """
    family_001_a -> family_001
    lawson_012_c -> lawson_012
    """
    parts = stem.split("_")
    return "_".join(parts[:2])


def get_store_name(stem: str) -> str:
    """
    family_001_a -> family
    mybasket_013_c -> mybasket
    """
    return stem.split("_")[0]


def copy_pair(image_path: Path, split: str):
    label_path = SRC_LABEL_DIR / f"{image_path.stem}.txt"

    if not label_path.exists():
        raise FileNotFoundError(f"Missing label for {image_path.name}")

    out_img_dir = OUT_DIR / "images" / split
    out_lbl_dir = OUT_DIR / "labels" / split

    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(image_path, out_img_dir / image_path.name)
    shutil.copy2(label_path, out_lbl_dir / label_path.name)


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    images = sorted([
        p for p in SRC_IMAGE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ])

    groups = defaultdict(list)
    for img in images:
        receipt_id = get_receipt_id(img.stem)
        groups[receipt_id].append(img)

    # 按便利店分组，再在每家里面随机分 train/val/test
    groups_by_store = defaultdict(list)
    for receipt_id, imgs in groups.items():
        store = get_store_name(receipt_id)
        groups_by_store[store].append((receipt_id, imgs))

    split_counts = Counter()
    image_counts = Counter()

    for store, receipt_groups in sorted(groups_by_store.items()):
        random.shuffle(receipt_groups)

        n = len(receipt_groups)
        n_train = int(n * TRAIN_RATIO)
        n_val = int(n * VAL_RATIO)

        train_groups = receipt_groups[:n_train]
        val_groups = receipt_groups[n_train:n_train + n_val]
        test_groups = receipt_groups[n_train + n_val:]

        split_map = {
            "train": train_groups,
            "val": val_groups,
            "test": test_groups,
        }

        print(f"\nStore: {store}")
        print(f"  receipt groups: {n}")
        print(f"  train: {len(train_groups)}, val: {len(val_groups)}, test: {len(test_groups)}")

        for split, group_list in split_map.items():
            for receipt_id, imgs in group_list:
                split_counts[(store, split)] += 1
                for img in imgs:
                    copy_pair(img, split)
                    image_counts[split] += 1

    print("\nImage counts:")
    for split in ["train", "val", "test"]:
        print(f"{split}: {image_counts[split]}")

    print("\nDone. Output:", OUT_DIR)


if __name__ == "__main__":
    main()

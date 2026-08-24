"""One-time script: downloads the full CIFAR-10 dataset and deterministically
selects `--per-class` real images per class, writing them into the
ImageFolder layout `ml/data/raw/<class_name>/` that the rest of the
pipeline already expects (`ml/training/dataset.py` works against any
ImageFolder-structured `raw_dir`, unmodified).

This replaces the tiny 60-images/class placeholder from
`ml/data/prepare_sample_dataset.py` (kept, not removed) with a real,
meaningfully-sized dataset: 300 images/class by default, 3,000 total,
drawn from CIFAR-10's 50,000-image `train=True` split — 5,000 images
available per class, so selecting 300 has zero risk of duplication.

Filenames use a `real_00001.png`-style scheme, deliberately distinct from
the placeholder's `<class>_0059.png` pattern, so it's visually obvious
which files are the real dataset.

Selection is deterministic: the same `seed` from `ml/configs/
train_config.yaml` (the single source of truth for it — constraints.md
rule 4) drives `random.Random(seed).sample(...)` over a sorted, stable
list of candidate indices, so re-running this script against the same
config always selects the same 300-per-class set.

DOWNLOAD SOURCE: a BrainChip-hosted mirror
(data.brainchip.com/dataset-mirror/cifar10/), not torchvision's default
`www.cs.toronto.edu` URL. The university server stalled for over 24 hours
on a first attempt — the connection stayed open and kept trickling bytes
(112MB -> 128MB over a full day) so nothing crashed or timed out, it just
never finished; torchvision's built-in downloader has no stall/progress
detection at all, so that failure was invisible until checked a day
later. (An initially-tried `ossci-datasets` S3 URL turned out not to host
CIFAR-10 at all — verified by listing the bucket, which only has
`mnist/torchbench/torchtune/tritonbench` — so it was never actually used.)
The mirror below was verified directly before use: reachable, correct
Content-Length (170,498,071 bytes, matching the known archive size),
`Accept-Ranges: bytes` supported, and ~3.9 MB/s measured — its actual
contents are still verified against the archive's real md5 below,
independent of the source. torchvision's `CIFAR10` class is still used
for everything AFTER the file is on disk (parsing the batches, labels,
`.targets`) — only the download step was replaced, with a custom stdlib-
only (`urllib`) downloader that adds a hard per-read stall timeout,
periodic progress logging, and resume support, none of which
torchvision's built-in downloader has.

Usage:
    python -m ml.data.prepare_real_dataset --config ml/configs/train_config.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import shutil
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from random import Random

from torchvision.datasets import CIFAR10

from ml.config import load_config

# CIFAR-10's fixed label order — the index a raw CIFAR-10 sample's label
# refers to. This is CIFAR-10-specific and has nothing to do with the
# project's own class list beyond matching names to indices below.
CIFAR10_LABEL_NAMES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck",
]

DEFAULT_IMAGES_PER_CLASS = 300

# Verified reachable + correct size before use (see module docstring).
# Same expected md5 as torchvision's default source — checked below
# regardless of which URL actually served the bytes.
CIFAR10_URL = "https://data.brainchip.com/dataset-mirror/cifar10/cifar-10-python.tar.gz"
CIFAR10_MD5 = "c58f30108f718f92721af3b95e74349a"
CIFAR10_ARCHIVE_NAME = "cifar-10-python.tar.gz"

STALL_TIMEOUT_SECONDS = 60
CHUNK_SIZE = 256 * 1024  # 256 KB
PROGRESS_LOG_INTERVAL_SECONDS = 12


def _md5sum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_with_resume(url: str, dest: Path, expected_md5: str) -> None:
    """Streams `url` to `dest`, resuming a partial `<dest>.part` file if one
    exists from a previous interrupted run. Raises `TimeoutError` if a
    single read stalls for `STALL_TIMEOUT_SECONDS` — unlike torchvision's
    built-in downloader, which has no such guard (see module docstring).
    """
    if dest.is_file() and _md5sum(dest) == expected_md5:
        print(f"{dest} already present and verified — skipping download.")
        return

    part_path = dest.with_suffix(dest.suffix + ".part")
    resume_from = part_path.stat().st_size if part_path.is_file() else 0

    request = urllib.request.Request(url)
    if resume_from:
        request.add_header("Range", f"bytes={resume_from}-")
        print(f"Resuming download from byte {resume_from:,}")

    # timeout= applies to each individual socket operation (connect and
    # every read), not the download as a whole — exactly the "N seconds of
    # zero progress" semantics we want, for free from the stdlib.
    try:
        response = urllib.request.urlopen(request, timeout=STALL_TIMEOUT_SECONDS)
    except urllib.error.HTTPError as exc:
        if exc.code == 416:  # Range Not Satisfiable -> already fully downloaded
            part_path.rename(dest)
            return
        raise

    resumed = resume_from and response.status == 206
    if resume_from and not resumed:
        print("Server did not honor the resume request — starting over.")
        resume_from = 0

    content_range = response.headers.get("Content-Range")
    content_length = response.headers.get("Content-Length")
    if resumed and content_range:
        total_size = int(content_range.rsplit("/", 1)[-1])
    elif content_length:
        total_size = int(content_length)
    else:
        total_size = None

    downloaded = resume_from
    start = time.monotonic()
    last_log = start

    with part_path.open("ab" if resumed else "wb") as f:
        while True:
            try:
                chunk = response.read(CHUNK_SIZE)
            except (TimeoutError, ConnectionError, http.client.IncompleteRead) as exc:
                raise TimeoutError(
                    f"Download stalled: no data received for "
                    f"{STALL_TIMEOUT_SECONDS}s ({downloaded:,} bytes received so "
                    f"far). Re-run this script to resume from {part_path}."
                ) from exc
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)

            now = time.monotonic()
            if now - last_log >= PROGRESS_LOG_INTERVAL_SECONDS:
                elapsed = now - start
                rate_kb_s = (downloaded - resume_from) / max(elapsed, 1e-3) / 1024
                if total_size:
                    pct = downloaded / total_size * 100
                    print(f"  {downloaded:,}/{total_size:,} bytes ({pct:.1f}%) — {rate_kb_s:.0f} KB/s")
                else:
                    print(f"  {downloaded:,} bytes — {rate_kb_s:.0f} KB/s")
                last_log = now

    actual_md5 = _md5sum(part_path)
    if actual_md5 != expected_md5:
        raise ValueError(
            f"Downloaded file's md5 ({actual_md5}) does not match the "
            f"expected ({expected_md5}) — corrupt/incomplete download. "
            f"Partial file kept at {part_path}; delete it to force a clean retry."
        )
    part_path.rename(dest)

    elapsed_total = time.monotonic() - start
    avg_kb_s = (downloaded - resume_from) / max(elapsed_total, 1e-3) / 1024
    print(f"Download complete: {downloaded:,} bytes total, "
          f"{elapsed_total:.0f}s this run, {avg_kb_s:.0f} KB/s average this run.")


def select_and_save(
    raw_dir: Path, classes: list[str], seed: int, images_per_class: int
) -> dict[str, int]:
    """Downloads CIFAR-10 (if not already cached) and writes exactly
    `images_per_class` real, distinct images per configured class into
    `raw_dir/<class_name>/`. Returns the actual per-class count written."""
    missing = set(classes) - set(CIFAR10_LABEL_NAMES)
    if missing:
        raise ValueError(
            f"prepare_real_dataset only knows how to source these classes "
            f"from CIFAR-10: {CIFAR10_LABEL_NAMES}. Unknown classes in "
            f"config: {sorted(missing)}"
        )

    download_dir = raw_dir.parent / ".cifar10_full_cache"
    download_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_dir / CIFAR10_ARCHIVE_NAME

    download_with_resume(CIFAR10_URL, archive_path, CIFAR10_MD5)

    print("Extracting archive...")
    with tarfile.open(archive_path) as tar:
        tar.extractall(download_dir, filter="data")

    # Everything past this point is unmodified torchvision — only the
    # download step above was replaced.
    dataset = CIFAR10(root=str(download_dir), train=True, download=False)

    # Group sample INDICES by class using dataset.targets (plain ints) —
    # not dataset[i], which would decode every one of the 50,000 images
    # via PIL just to read a label. Only the ~300/class actually selected
    # below get decoded.
    indices_by_class: dict[str, list[int]] = {name: [] for name in classes}
    for idx, label_idx in enumerate(dataset.targets):
        class_name = CIFAR10_LABEL_NAMES[label_idx]
        if class_name in indices_by_class:
            indices_by_class[class_name].append(idx)

    rng = Random(seed)
    counts: dict[str, int] = {}

    for class_name in classes:
        available = sorted(indices_by_class[class_name])  # stable order first
        if len(available) < images_per_class:
            raise RuntimeError(
                f"Only {len(available)} CIFAR-10 train samples available for "
                f"class '{class_name}', need {images_per_class}."
            )
        selected_indices = rng.sample(available, images_per_class)

        class_dir = raw_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        for n, idx in enumerate(selected_indices, start=1):
            image, _ = dataset[idx]  # decode only the selected image
            out_path = class_dir / f"real_{n:05d}.png"
            image.save(out_path)
        counts[class_name] = len(selected_indices)

    shutil.rmtree(download_dir, ignore_errors=True)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("ml/configs/train_config.yaml")
    )
    parser.add_argument(
        "--per-class",
        type=int,
        default=DEFAULT_IMAGES_PER_CLASS,
        help="Number of real images to select per class.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    raw_dir = Path(config["dataset"]["raw_dir"])
    classes = config["dataset"]["classes"]
    seed = config["seed"]

    already_populated = raw_dir.is_dir() and any(
        f.is_file() for f in raw_dir.rglob("*")
    )
    if already_populated:
        print(f"{raw_dir} already has files in it — skipping. Clear it first to regenerate.")
        return

    counts = select_and_save(raw_dir, classes, seed, args.per_class)

    print("Wrote real CIFAR-10 images:")
    for class_name in classes:
        print(f"  {class_name}: {counts[class_name]}")
    total = sum(counts.values())
    all_match = all(c == args.per_class for c in counts.values())
    print(f"Total: {total} images across {len(classes)} classes "
          f"({'OK — exactly ' + str(args.per_class) + '/class' if all_match else 'MISMATCH'})")


if __name__ == "__main__":
    main()

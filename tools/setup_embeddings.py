"""Download and verify the pinned local Qwen3 embedding model."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from embeddings.qwen3 import MODEL_DIRECTORY, download_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIRECTORY)
    parser.add_argument("--install-dependencies", action="store_true", help="Install the pinned Windows/Python 3.13 CUDA 12.6 runtime")
    args = parser.parse_args()
    if args.install_dependencies:
        temporary, cache = ROOT / ".cache/pip-tmp", ROOT / ".cache/pip"
        temporary.mkdir(parents=True, exist_ok=True); cache.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ, TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary), PIP_CACHE_DIR=str(cache))
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r",
                        str(ROOT / "requirements-embedding.txt")], env=environment, check=True)
    print(download_model(args.model_dir), flush=True)


if __name__ == "__main__":
    main()

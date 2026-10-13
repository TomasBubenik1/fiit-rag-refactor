"""Install pinned Tesseract language data locally; PDF contents are never uploaded."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import ssl
from urllib.request import urlopen

import certifi


REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / ".cache" / "tessdata"


def install_models(languages, directory=DEFAULT_DIRECTORY):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context(cafile=certifi.where())
    installed = []
    for language in languages:
        if not re.fullmatch(r"[a-z_]{3,30}", language):
            raise ValueError(f"Invalid OCR language code: {language}")
        target = directory / f"{language}.traineddata"
        url = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{REVISION}/{target.name}"
        with urlopen(url, context=context, timeout=60) as response:
            data = response.read()
        temporary = target.with_suffix(".download")
        temporary.write_bytes(data)
        temporary.replace(target)
        installed.append({"language": language, "url": url, "sha256": hashlib.sha256(data).hexdigest()})
        print(f"Installed {language}: {target}", flush=True)
    (directory / "source.json").write_text(json.dumps({"revision": REVISION, "models": installed}, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--languages", nargs="+", default=["slk", "eng"])
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    install_models(args.languages, args.directory)


if __name__ == "__main__":
    main()

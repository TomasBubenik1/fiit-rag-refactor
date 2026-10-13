# Chunking methods

Each method lives in one Python file. Its helpers belong in that same file.

`block_aware.py` contains the existing method: a soft target of 2,400 characters,
whole Markdown blocks, intact tables/code, heading context, and no overlap.

`token_aware.py` provides `split_chunk(chunk, tokenizer, max_tokens=2048)` for
embedding inputs. It counts the actual tokenizer's tokens including context,
splits oversized tables by rows with repeated headers/rowspan values, and keeps
parent/source references. It leaves the original block-aware chunks unchanged.

## Use the cleaned corpus independently

`data/normalized/documents/*.md`, `documents/*.json`, and `corpus.jsonl` contain
the cleaned content before chunking. The `chunks.*.jsonl` files are derived
outputs. You can read the cleaned documents or run another chunking method
without parsing the original HTML/PDFs again.

The method accepts a cleaned document and one of its segments. It yields chunk
records and does not modify either input:

```python
import json
from pathlib import Path

from chunking.block_aware import chunk_segment

with Path("data/normalized/corpus.jsonl").open(encoding="utf-8") as corpus:
    for line in corpus:
        document = json.loads(line)
        for segment in document["segments"]:
            for chunk in chunk_segment(segment, document, target=2400):
                # Use or write this chunk in your retrieval pipeline.
                pass
```

For an additional method, create a separate module here and keep the same
`chunk_segment(segment, document, target=...)` interface if it needs to plug
into the existing normalization pipeline. Methods can use their own settings.

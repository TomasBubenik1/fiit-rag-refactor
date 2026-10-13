# Spracovanie uloženého HTML a PDF

HTML parser pracuje s dodaným snapshotom FIIT. Vyberie hlavný nadpis a bloky
`.section-info-page-content` v `.content-section`, následne ich prevedie do
Markdownu. Navigácia, pätička, zdieľanie a spätná väzba sa do výstupu nedostanú.
Nadpisy, zoznamy, odkazy a jednoduché tabuľky zostávajú zachované. Tabuľky so
zlúčenými bunkami alebo neúplnou štruktúrou riadkov zostávajú v Markdowne ako HTML,
aby sa nestratili údaje ani ich vzťahy.

Kód používa obyčajné funkcie, bez vlastných tried. Výber HTML a jeho prevod do
Markdownu sú oddelené, aby sa dali čítať a upravovať samostatne.

Z koreňa projektu v PowerShelli:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-parser.txt
.\.venv\Scripts\python.exe tools/extract_main_content.py data/raw_html/harmonogram-studia.html
```

Výstup je v `data/clean_markdown`: `.md`, sprievodné `.html` na kontrolu štruktúry
a `.json` so zdrojovou URL. Pôvodné súbory parser neprepisuje. Možno zadať viac
HTML súborov alebo samostatný `--output-dir`. Zdrojové URL číta z
`data/url_mapping.json`; pre jeden súbor ich možno zadať cez `--source-url`.

Metadata obsahujú aj `linked_pdf_urls`. Vyčistená stránka môže byť len rozcestník:
pre odpovede chatbota treba spracovať aj obsah odkazovaných PDF ako samostatné
dokumenty s ich zdrojovou URL a akademickým rokom. Pri harmonograme už v balíku
existuje `data/markdown/harmonogram_2526_2026-02-06.md` a pôvodné PDF v `raw_pdfs`.
HTML skript iba zaznamená odkazy; obsah PDF automaticky neimportuje.

Vložený kalendár sa zachová ako odkaz. Jeho udalosti sa nesťahujú. HTML parser zatiaľ
spracúva túto šablónu uložených HTML, nie aktuálnu verziu celého webu.
Stránku bez očakávaného kontajnera ohlási ako chybu namiesto exportu celého webového
rozhrania. Pri nových šablónach treba pridať a overiť ďalšie pravidlá výberu obsahu.

## PDF harmonogram

```powershell
.\.venv\Scripts\python.exe tools/parse_harmonogram_pdf.py data/raw_pdfs/harmonogram_2526_2026-02-06.pdf
```

PDF parser používa funkcie a `pdfplumber`. Číta text a polohu slov priamo z PDF.
V sekciách s dvomi samostatnými zoznamami prečíta najprv ľavý a potom pravý stĺpec.
Spája názov udalosti s dátumom a časom; rozlíši napríklad odovzdanie BP2 od jeho
obhajoby. Termíny sa v kóde nenachádzajú, číta ich z dokumentu.

Výstupom sú `.md` a `.json` v `data/clean_markdown`. JSON obsahuje sekcie, udalosti,
zdrojovú stranu a polohu každého termínu, URL, akademické roky a dátum platnosti
údajov uvedený v PDF. Opakované upozornenie z pätičiek zostáva vo výstupe raz.
HTML stránka a PDF zostávajú samostatnými dokumentmi.

Toto je prvý profil pre šablónu semestrálneho harmonogramu, overený na uvedenom
trojstranovom PDF. Nejde o univerzálny parser všetkých PDF; katalógy predmetov,
iné rozloženia a skenované dokumenty budú potrebovať vlastné pravidlá alebo OCR.

Overenie proti termínom prečítaným z pôvodného PDF:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Všeobecný PDF parser

Odporúčaný vstupný bod pre rôzne PDF je teraz `tools/parse_pdf.py`. Používa
PyMuPDF4LLM na rozloženie, text, nadpisy a tabuľky. Pri tabuľkách s čiarami
rekonštruuje skutočné bunky z PDF vrátane zlúčených buniek. Pre harmonogram sa
automaticky použije už overený profil; ostatné PDF nepotrebujú pravidlá podľa
názvu súboru. Náš kód používa funkcie bez vlastných tried.

Inštalácia a príklad z koreňa projektu:

```powershell
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements-parser.txt
.\.venv\Scripts\python.exe tools/setup_pdf_ocr.py
.\.venv\Scripts\python.exe tools/parse_pdf.py data/raw_pdfs/harmonogram_2526_2026-02-06.pdf data/raw_pdfs/katalog-predmetov_2025-26.pdf
```

OCR používa lokálne modely pre slovenčinu a angličtinu. Inštalačný skript sťahuje
iba jazykové modely z pevnej revízie oficiálneho repozitára Tesseract. Ukladá ich
do `.cache/tessdata`; samotné dokumenty sa spracúvajú lokálne. Pre iné jazyky:

```powershell
.\.venv\Scripts\python.exe tools/setup_pdf_ocr.py --languages slk eng deu
.\.venv\Scripts\python.exe tools/parse_pdf.py cesta/k/dokumentu.pdf --language slk+eng+deu
```

Celý priečinok vrátane podpriečinkov:

```powershell
.\.venv\Scripts\python.exe tools/parse_pdf.py data/raw_pdfs
```

Výstupy sú v `data/parsed_pdf`, oddelene od pôvodných dát aj výstupov prvého
prototypu. Každý súbor dostane Markdown, JSON a priečinok `.assets` s extrahovanými
obrázkami. `batch_report.json` uvádza výsledok aktuálneho behu. Chybný alebo
zamknutý súbor sa zapíše ako chyba a ostatné sa spracujú ďalej.

JSON obsahuje strany, text, súradnice rozloženia, polia formulárov, odkazy,
zdrojovú URL a kontrolný súčet vstupu. Hlavičky a pätičky sa vynechajú z hlavného
Markdownu, ale zostávajú v JSON na kontrolu. `native_text` je pôvodná textová
vrstva; `full_markdown` zachováva aj vynechané časti a k nemu sa vzťahujú pozície
v `layout_boxes`. Stav `parsed` znamená dokončenie bez automaticky zistených
problémov, nie záruku úplnej významovej správnosti.

Stav `needs_review` označuje OCR, chýbajúci text, nečitateľné znaky, neistú
štruktúru tabuľky, možné oddelenie názvov a hodnôt alebo vizuálny obsah. Pri veľmi
malom množstve získaného textu sa uloží aj obraz celej strany na kontrolu.
Takéto výsledky treba preveriť pred zaradením do znalostnej bázy. Zložité grafy,
vzorce, obrázkové plagáty a nekvalitné skeny nemajú garantovaný bezchybný textový
výstup. Parser ich označí; význam grafu automaticky nevysvetľuje.

Užitočné prepínače:

- `--pages 1 2 15`: spracuje iba uvedené strany, výsledok má `partial: true`.
- `--ocr off`: vypne OCR; obrazové strany zostanú označené na kontrolu.
- `--ocr force`: vynúti OCR, napríklad pri poškodenej textovej vrstve.
- `--generic`: vynechá špecifický profil harmonogramu.
- `--no-images`: neexportuje obrázky ani náhľady na kontrolu.
- `--password-env PDF_PARSER_PASSWORD`: načíta heslo zo zvolenej premennej
  prostredia. Heslo sa neukladá do výstupov.
- `--output-dir cesta/k/vystupu`: zmení cieľový priečinok.

Testy pokrývajú obsah harmonogramu, bunky katalógu vrátane kreditov, OCR skenu,
číslovanie strán, explicitne vypnuté OCR, pokračovanie dávky po chybe a zachovanie
pôvodných dát. OCR testy vyžadujú predchádzajúce spustenie inštalačného skriptu.

## Normalizacia celeho poskytnuteho balika

`normalize_dataset.py` spracuje HTML, RSS a podporne subory; `batch_dataset_pdfs.py` spracuje vsetky PDF vratane nespravnych pripon a ulozi checkpointy. Pouzivaju obycajne funkcie. Povodne subory zostavaju zachovane.

Chunkovanie je v samostatnom priecinku `chunking/`; kazda metoda ma vlastny subor. Aktualna metoda je `chunking/block_aware.py`. Vycistene Markdown/JSON dokumenty a `corpus.jsonl` sa daju pouzit aj s inou metodou, bez opakovaneho parsovania zdrojov. Priklady pouzitia su v `chunking/README.md`.

```powershell
.\.venv\Scripts\python.exe tools/normalize_dataset.py --stage web
.\.venv\Scripts\python.exe tools/batch_dataset_pdfs.py --workers 6
.\.venv\Scripts\python.exe tools/normalize_dataset.py --stage finalize
.\.venv\Scripts\python.exe tools/validate_normalized_dataset.py
```

Vystup: `data/normalized/README.md` (format), `INDEX.md` (citatelny zoznam dokumentov), `corpus.jsonl`, `chunks.ready.jsonl` a `chunks.review.jsonl`. JSON dokumenty uchovavaju povodny zdroj, URL, cislo strany, odkazy a upozornenia. Zlozite tabulky sa nedelia medzi chunky. Povodne Markdown kopie sa mapuju na normalizovane zdroje, aby sa obsah neindexoval dvakrat. Binarny model, grafy a SQLite SHM sa zachovavaju cez povodne cesty a kontrolne sucty; ostatne podporne zaznamy maju samostatne exporty.

PDF cache sa overuje podla SHA-256 vstupu a verzie parsera. Preruseny dokument sa spracuje znovu; hotove dokumenty sa preskocia. `validate_normalized_dataset.py` kontroluje pokrytie stran, odkazy na zdroje, smerovanie chunkov a nezmenene originaly.

## Lokalne embeddingy Qwen3

`embeddings/qwen3.py` nacitava lokalny Qwen3-Embedding-0.6B. Nastavenie pre GTX 1080 Ti pouziva PyTorch CUDA 12.6 a FP32. Instalator uklada docasne subory/cache na disk projektu. Model je pripnuty na konkretnu reviziu a kontrolne sucty.

```powershell
.\.venv\Scripts\python.exe tools/setup_embeddings.py --install-dependencies
.\.venv\Scripts\python.exe tools/embed_chunks.py
.\.venv\Scripts\python.exe tools/search_embeddings.py "Kedy sa zacina letny semester 2025/26?"
```

Vycistene data zostavaju zachovane. `chunking/token_aware.py` rozdeli iba prilis dlhe embeddingove vstupy podla skutocneho tokenizeru, so zachovanim odkazov na povodne chunky. Index ma vektory a metadata v `data/embeddings/qwen3-0.6b/`. Podrobnosti a moznosti obnovenia spracovania su v `embeddings/README.md`.

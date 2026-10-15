# FIIT QA – testovací dataset v slovenčine

120 otázok vytvorených podľa lokálneho normalizovaného korpusu FIIT STU:
100 zodpovedateľných, 10 vyžadujúcich upresnenie a 10 nezodpovedateľných
z uložených verejných dokumentov. Pozitívne odpovede majú 182 presných
citovaných úryvkov zo 47 chunkov a 19 dokumentov. Korpus pri vytvorení obsahoval
2 214 dokumentov a 9 580 ready chunkov.

Otázky a odpovede vytvoril asistent po kontrole zdrojov. Nejde o nezávisle
odborne schválený benchmark. Dátumy, osoby, ceny a pravidlá sú tvrdenia
uloženého snapshotu, nie potvrdenie ich dnešnej platnosti. Web sa nesťahoval.
Pred použitím ako finálneho benchmarku odporúčame ľudskú kontrolu anotácií.

## Súbory

| Súbor | Použitie |
| --- | --- |
| `dataset.jsonl` | Kompletné otázky, referenčné odpovede, kritériá a dôkazy. |
| `questions.jsonl` | Iba ID, otázka, jazyk a split; vstup pre testovaný systém. |
| `PREHLAD.md` | Čitateľný prehľad otázok, odpovedí a zdrojových odkazov. |
| `manifest.json` | Počty, metodika, obmedzenia a SHA-256 odtlačky datasetu a korpusu. |

Všetky súbory používajú UTF-8. Jeden riadok JSONL je jeden objekt.
Textové artefakty používajú konce riadkov LF, aby kontrolné súčty zostali
stabilné aj po klonovaní na Windows.
Pôvodné `data/eval_dataset.json` ani spracované zdroje sa nemenili.
Nový dataset má vlastnú schému; nejde o priamu náhradu pôvodného JSON zoznamu.

## Pokrytie

| Oblasť | Počet vrátane otázok na upresnenie a nezodpovedateľných otázok |
| --- | ---: |
| Harmonogram, termíny, obhajoby, promócie | 21 |
| Bakalárske prijímacie konanie | 16 |
| Inžinierske prijímacie konanie | 11 |
| Predmety a katalóg | 17 |
| Bakalárske projekty a záverečné práce | 11 |
| Erasmus+ | 8 |
| Ubytovanie | 10 |
| Študijné oddelenie a knižnica | 10 |
| Štipendiá a poplatky | 6 |
| Zápis a preukazy | 9 |
| Otázka mimo domény | 1 |

Sada obsahuje otázky bez diakritiky, postupy, porovnania, tri otázky vyžadujúce
viac zdrojových chunkov a otázky s nesprávnym predpokladom. Časové otázky
rozlišujú akademické roky 2025/26 a 2026/27, odovzdanie od obhajoby a výučbu
od skúškového obdobia. Ide o vybrané študentské témy, nie o úplné pokrytie
všetkých dokumentov fakulty.

Pri anotovaní sa použili iba znalostné ready chunky bez výstrah extrakcie.
OCR/review chunky, analytika a súkromné interakčné logy netvoria dôkazy odpovedí.
Stránka E-zápis má rozporný rok v nadpise; otázka na termíny zápisu preto
vychádza zo stránky Administrácia zápisov. Katalóg označuje garanta predmetu;
dataset z tohto údaja nevyvodzuje, kto reálne prednáša.

## Polia záznamu

- `id`, `query`, `language`: stabilný identifikátor, otázka a jazyk `sk`.
- `answerability`: `answerable`, `needs_clarification` alebo `unanswerable`.
- `reference_answer`, `required_facts`: vzorová odpoveď a fakty či správanie,
  ktoré treba pri hodnotení overiť. Doslovná zhoda odpovede sa nevyžaduje.
- `missing_information`, `forbidden_claims`: čo treba upresniť a ktoré
  nepodložené tvrdenia by boli chybou pri negatívnych príkladoch.
- `category`, `type`, `difficulty`, `query_style`, `academic_years`: tematické
  a pracovné anotácie; náročnosť je odhad anotátora, nie nameraný výsledok.
- `evidence`: pôvodné chunk/document ID, URL, súbor, číslo strany PDF od 1
  a presné úryvky. `start` a `end` sú indexy znakov Python reťazca v pôvodnom
  `chunk.text`; interval je `[start, end)`, nie bajtové pozície. HTML nemá stranu.
  `source_valid_as_of` kopíruje dostupné metadáta zdroja; neznáma platnosť je `null`.
- `support_sets`: každá vnútorná množina obsahuje zameniteľné chunky pre jeden
  potrebný dôkaz. Na úplné pokrytie treba aspoň jeden chunk z **každej** množiny.
  Alternatívy sú kontrolované obsahovo identické HTML dokumenty s rôznymi URL.
  Historické vydania PDF sa nezlučujú.
- `relevant_chunk_ids`, `relevant_document_ids`: zjednotenie známych relevantných
  ID. Nie sú to vyčerpávajúce úsudky o všetkých možných správnych zdrojoch.
- `split`, `group_id`: vývojová/testovacia časť a skupina pre delenie zdrojov.
- `annotation_status`, `annotation_note`: pôvod a upozornenia k anotácii.

Pri nezodpovedateľných a nejednoznačných otázkach sú pozitívne retrieval ID
a dôkazy prázdne. Nepovažujte akýkoľvek nájdený podobný dokument za správnu odpoveď.
Upresnenie môže sprevádzať prehľad možností; model nemá vybrať jednu bez kontextu.
Pri otázkach na živé či osobné údaje má uviesť obmedzenie a vhodný ďalší krok.

## Rozdelenie a použitie

`dev` má 30 otázok (25 zodpovedateľných, 3 na upresnenie, 2 nezodpovedateľné),
`test` 90 (75 zodpovedateľných, 7 na upresnenie, 8 nezodpovedateľných).
Vývojová sada bola vybraná tak, aby zastúpila všetkých desať študentských oblastí.
Po nastavení retrievalu, prahov alebo promptu na `dev` vyhodnoťte uzamknutý `test`.

Prepojené dôkazové chunky, ich obsahovo identické HTML aliasy a otázky s viacerými
takými chunkmi zostávajú v jednom splite. Rôzne chunky z rovnakého dokumentu
môžu byť v oboch splitoch. Rozdelenie teda nie je podľa celých dokumentov,
nie je náhodnou reprezentatívnou vzorkou a nie je určené ako train/test delenie.

Testovanému modelu dávajte `questions.jsonl` a bežný prístup k znalostnému
korpusu. Referenčné odpovede, citácie a tento priečinok nevkladajte do
retrieval indexu. Pri chunkovaní inou metódou premapujte dôkazy podľa dokumentu,
strany a úryvkov; uvedené chunk ID platia pre súčasný block-aware korpus.

Overenie datasetu z koreňa projektu, bez externých balíkov:

```powershell
.\.venv\Scripts\python.exe tools/validate_qa_dataset.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_qa_dataset.py -v
```

Validátor kontroluje schému, jednoznačnosť otázok, existenciu a ready stav zdrojov,
strany/URL, presné pozície úryvkov, HTML alternatívy, oddelenie chunkov medzi
splitmi, zhodu slepého exportu a kontrolné súčty. Potrebuje pôvodný lokálny
`data/normalized/`. Úspech dokazuje integritu a väzby, nie úplnú sémantickú
správnosť odpovedí. SHA-256 v manifeste identifikuje verziu; pri zámernej zmene
anotácií treba skontrolovať a aktualizovať aj odvodené súbory a manifest.

## Vyhodnotenie uloženého retrievalu

Uložte výsledky svojho systému ako JSONL, napríklad:

```json
{"id":"fiit-qa-0001","retrieved_chunk_ids":["pdf-479859f0392f5224bf09:p1:c0000"],"answerability":"answerable"}
```

`retrieved_chunk_ids` je zoradený zoznam unikátnych pôvodných ID z normalizovaného
korpusu. Pri token-aware embedding chunkoch použite `parent_chunk_id`; ak sa
rodič opakuje, ponechajte jeho prvý výskyt. Metriky potom opisujú poradie unikátnych
rodičovských chunkov. `answerability` je voliteľná predikcia troch tried.

```powershell
.\.venv\Scripts\python.exe tools/evaluate_qa_retrieval.py data/qa_predictions.jsonl --split test --top-k 5 --output data/qa_metrics.json
```

Skript meria podiel otázok s aspoň jedným známym dôkazom (`known_evidence_hit@k`),
MRR prvého takého dôkazu, priemerné pokrytie potrebných množín (`evidence_coverage@k`)
a podiel úplne pokrytých otázok (`complete_support@k`). Do týchto metrík vstupuje
iba 100 zodpovedateľných otázok, respektíve 75 pri predvolenom splite `test`.
Chýbajúci výsledok vo vybranom splite sa počíta ako neúspech. Neznáme alebo
duplicitné ID otázok sú chyba; výsledky z druhého známeho splitu sa ignorujú.

Presnosť `answerability_accuracy` zahŕňa všetky otázky vybraného splitu. Ak nie sú
dodané žiadne predikcie tejto triedy, je `null`; pri čiastočnom pokrytí sa
chýbajúce klasifikácie počítajú ako nesprávne. Výstup má aj rozpis podľa kategórií,
požadovaného správania a jednotlivých otázok.

Tieto skóre hodnotia iba známe dôkazy a klasifikáciu správania. Odpoveď, citácie,
faktickú správnosť a neprítomnosť nepodložených tvrdení treba hodnotiť samostatne
podľa `required_facts`, `forbidden_claims` a zdrojov. Hodnotenie správnych zdrojov
je neúplné, preto skript neuvádza precision ani úplný recall.

V tomto pracovnom priečinku pri tvorbe datasetu nebol embeddingový index.
Kvalita konkrétneho retrievalu ani generovaných odpovedí preto zatiaľ nebola
zmeraná. Testy vyhodnocovača používajú syntetické výsledky vrátane ideálneho
výberu známych dôkazov; nejde o výsledky modelu.

# Rozsah práce: konverzačný RAG pre byrokratické inštitúcie

Tento dokument zachytáva zadanie a spresnenie rozsahu od používateľa. FIIT je
prvý korpus a prípadová štúdia; výsledný systém má byť použiteľný aj nad ďalšími
inštitucionálnymi dokumentmi. Prvým príkladom organizačnej hierarchie je FIIT → STU.
Opisované rozšírenia sú plán práce, nie tvrdenie o už hotovej implementácii.

## Text zadania

> V dnešnej dobe sa čoraz intenzívnejšie využívajú veľké jazykové modely umelej inteligencie, ktoré automatizujú rutinné úlohy a zvyšujú efektivitu práce. Ich schopnosť generovať odpovede je však limitovaná dostupnými znalosťami modelu a môže viesť k nepresnostiam alebo halucináciám. Prístup Retrieval-Augmented Generation (RAG) umožňuje tieto nedostatky zmierniť kombináciou generovania a vyhľadávania relevantných externých informácií.

> Analyzujte existujúce prístupy, architektúry a nástroje ako napr. RAG versus agentic RAG, MPC versus RPC, databázy versus vektorové databázy. Navrhnite a implementujte vlastný RAG systém vhodný na konverzačnú komunikáciu. Riešenie evaluujte pomocou vhodných metrík a experimentovania na verejných datasetoch a realistických scenároch.

## Čo má byť výsledkom

| Požiadavka | Výstup / úloha v pláne |
| --- | --- |
| Analýza RAG a agentic RAG | S00: porovnanie riadenia, nástrojov, kvality dôkazov a nákladov; zdôvodnený výber architektúry. |
| Analýza „MPC versus RPC“ | S00: najprv potvrdiť význam MPC s vedúcim; neprepisovať zadanie potichu. |
| Databázy a vektorové databázy | S00 + S05: porovnanie podľa požiadaviek a implementácia zvoleného úložiska a rozhraní. |
| Vlastný konverzačný RAG | E00–E08 + S03: ingestion, retrieval, generovanie so zdrojmi, história dialógu a upresňovanie otázok. |
| Inštitúcie a ich vzťahy | S01 + S04: adaptéry korpusov, pôsobnosť dokumentov a scenáre FIIT → STU. |
| Verejné datasety | S02 + E09: výber, verzie, adaptéry, oddelené splity a merania na verejných benchmarkoch. |
| Realistické scenáre | S04 + E09: postupy, termíny, podmienky, dokumenty z viacerých úrovní a nadväzujúce otázky. |

Analýza alternatív je povinná. Implementácia všetkých alternatív z nej automaticky
nevyplýva: základ tvorí jeden funkčný, zdôvodnený konverzačný RAG. Agentný prototyp
alebo ďalšie databázové backendy sa implementujú, ak ich vyberie návrh alebo
samostatný experiment s kontrolným variantom a rozpočtom.

## Doména a inštitucionálna hierarchia

- **Začiatok:** existujúce dokumenty FIIT a lokálny QA benchmark.
- **Prvé rozšírenie:** samostatne verziovaná vzorka dokumentov STU a vzťah FIIT → STU.
- **Prenositeľnosť:** ďalší korpus sa pripája adaptérom a spoločnou schémou,
  nie prepisom konverzačnej aplikácie.
- **Metadáta:** zdroj, dokument, inštitúcia, nadradená organizácia, pôsobnosť,
  časová platnosť, URL, strana, nadpisy a pôvod úryvku.
- **Rozpory:** organizačný rodič neurčuje automaticky nadradenosť každého pravidla.
  Treba overiť pôsobnosť, platnosť a explicitné výnimky; nejasný prípad vyžaduje
  upresnenie alebo vysvetlenie rozporu so zdrojmi.
- **Dialóg:** udržať požadovanú inštitúciu a obdobie, rozumieť nadväzujúcim otázkam
  a umožniť zmenu témy či reset kontextu.

## Verejné dáta a realistické hodnotenie

[Doc2Dial](https://doc2dial.github.io/) je kandidát na dokumentovo podložené
dialógy z verejných informačných služieb. [MultiDoc2Dial](https://doc2dial.github.io/multidoc2dial/data_readme.html)
je príbuzný kandidát pre dialógy nad viacerými dokumentmi. Pred výberom overiť
licenciu, skutočne dostupné splity, prekrytie datasetov a mapovanie dôkazov.
Dokumentácia MultiDoc2Dial v1.0 upozorňuje na zástupný testovací súbor; nepovažovať
ho za plnohodnotnú testovaciu sadu bez overenia použitej verzie.

FIIT/slovenské výsledky, výsledky verejných benchmarkov a vlastné FIIT → STU
scenáre vykazovať oddelene. Rozlišovať kvalitu vyhľadania, oporu odpovede,
správnosť citácií, výber inštitúcie/obdobia, splnenie krokov postupu, upresnenie,
správanie počas dialógu, latenciu a pamäť. Referenčné odpovede ani budúce ťahy
dialógu nesmú uniknúť do retrieval indexu alebo vstupu hodnoteného ťahu.

## Otvorená terminológia: MPC

Zadanie uvádza **MPC**, nie MCP. Význam musí potvrdiť vedúci. Ak bolo myslené
**MCP**, [jeho špecifikácia](https://modelcontextprotocol.io/specification/2026-07-28)
uvádza komunikáciu pomocou JSON-RPC 2.0: porovnanie má vysvetliť vrstvy,
účel a integračné možnosti, nie ich označiť za vzájomne sa vylučujúce mechanizmy.

## Pracovné dokumenty

- [Plán experimentov](plan_experimentov.md): technický protokol; FIIT je prvý scenár.
- [Kontrolný zoznam a odkazy do Plane](project_checklist.md): rozdelenie práce.
- [Osnova práce](osnova_bakalarskej_prace.md): kapitoly, ktoré musia pokryť celé zadanie.

Plane je zdroj živého stavu úloh. Tieto dokumenty uchovávajú rozsah, protokol
a rozhodnutia; neoznačujú plánované časti za implementované.

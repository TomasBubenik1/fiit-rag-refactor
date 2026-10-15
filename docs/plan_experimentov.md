# Plán experimentov pre konverzačný RAG

Pracovný návrh z 15. 10. 2026. Dokument zhŕňa modely, retrieval metódy a ostatné nastavenia; slovenský korpus FIIT STU tvorí prvú prípadovú štúdiu. Celé zadanie smeruje ku konverzačnému RAG pre byrokratické inštitúcie, nie iba k vyhľadávaniu na webe FIIT. Záväzný rámec a pôvodné znenie sú v [rozsahu práce](project_scope.md). Je to plán meraní; neobsahuje namerané výsledky ani tvrdenie, že navrhnuté varianty už fungujú.

**Jadro** označuje hlavné plánované porovnania. **Rozšírenie** zaradíme podľa času, dostupného hardvéru a chýb zistených v jadre. Nebudeme skúšať kartézsky súčin všetkých modelov a nastavení: najprv porovnáme jednotlivé časti, potom zostavíme a overíme výslednú konfiguráciu.

## 0. Rozsah celého systému

Existujúce experimenty E00–E09 zostávajú technickým jadrom. Súbežné úlohy
rozširujú návrh a hodnotenie podľa zadania:

| Úloha | Povinný výstup |
| --- | --- |
| S00 | Analýza RAG/agentic RAG, databáz/vektorových databáz a významu „MPC versus RPC“; zdôvodnená architektúra. |
| S01 | Adaptéry korpusov a metadáta inštitúcie, nadradenej organizácie, pôsobnosti a platnosti; FIIT → STU ako prvý príklad. |
| S02 | Verejné dialógové datasety, overené verzie/splity, mapovanie dôkazov a metriky mimo lokálneho FIIT benchmarku. |
| S05 | Implementácia vybraných úložísk a rozhraní; ďalšie backendy/protokoly len podľa návrhu alebo konkrétneho experimentu. |
| S03 | Funkčná konverzačná aplikácia s históriou, nadväzujúcimi otázkami, citáciami a upresňovaním. |
| S04 | Realistické byrokratické postupy a otázky naprieč úrovňami FIIT/STU vrátane pôsobnosti, výnimiek a rozporov. |

Pred uzamknutím konfigurácie v E08 musia byť pripravené verejné hodnotenie,
konverzačný tok a inštitucionálne scenáre. E09 vykáže ich výsledky oddelene
od lokálneho FIIT retrievalu. Generovanie a konverzácia patria do požadovaného
výsledku. Analýza agentic RAG je povinná; implementácia agentného variantu nie
je automaticky povinná. Význam skratky MPC treba potvrdiť, nie potichu zmeniť.

## 1. Z čoho vychádzame

| Časť | Aktuálny stav v projekte |
| --- | --- |
| Dáta | Normalizované HTML/PDF, zdrojové URL, strany, nadpisy, dostupné časové metadáta a upozornenia na kvalitu. |
| Chunkovanie | `block_aware`: mäkký cieľ 2 400 **znakov**, celé obsahové bloky a tabuľky, bez overlapu. Následne `token_aware` rozdelí príliš dlhé embeddingové vstupy. |
| Embedding | Implementovaný `Qwen/Qwen3-Embedding-0.6B`, revízia `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, FP32, normalizované 1 024-rozmerné vektory, predvolený rozpočet 2 048 tokenov. |
| Retrieval | Presné vektorové vyhľadávanie cez NumPy a kosínusovú podobnosť; predvolene top 5. |
| Benchmark | `evaluation/fiit_qa/`: 120 otázok, referenčné odpovede a konkrétne dôkazy. |
| Vyhodnotenie | Existuje validátor datasetu a vyhodnotenie uložených retrieval predikcií. |
| Chýbajúce vrstvy | BM25, hybrid, reranking a generovanie odpovedí sú v tomto pláne nové experimentálne varianty. |

Počty uloženého snapshotu: **2 214 dokumentov a 9 580 ready chunkov**. Indexujeme znalostný obsah; referenčné odpovede, evaluačné súbory ani podporné logy nepatria do indexu. Implementácia základného retrievalu existuje, ale výsledky na novom 120-otázkovom benchmarku treba ešte zmerať. Staršie ukážkové výsledky v README nenahrádzajú toto meranie.

Podklady: [hlavné README](../README.md), [embeddingy](../embeddings/README.md), [chunkovanie](../chunking/README.md), [benchmark a jeho obmedzenia](../evaluation/fiit_qa/README.md).

## 2. Embeddingové modely

Embeddingový model vytvára reprezentáciu otázky a textu na vyhľadávanie. Odpoveď pre používateľa bude vytvárať samostatný generatívny model.

| Model – presný identifikátor a dokumentácia | Rozsah | Rozmer vektora | Limit vstupu podľa modelovej karty | Čo ním overíme |
| --- | --- | ---: | ---: | --- |
| [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Jadro; existujúci základ | 1 024 | 32 768 tokenov | Východisková kvalita a náklady súčasného riešenia. |
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | Jadro; najprv dense režim | 1 024 | 8 192 tokenov | Alternatívna viacjazyčná reprezentácia; neskôr aj sparse a multi-vector režim. |
| [intfloat/multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) | Jadro | 768 | 512 tokenov | Menší model ako porovnanie kvality, rýchlosti a veľkosti indexu. |
| [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) | Jadro | 1 024 | 512 tokenov | Vplyv veľkosti v rámci rovnakej rodiny E5. |
| [intfloat/multilingual-e5-large-instruct](https://huggingface.co/intfloat/multilingual-e5-large-instruct) | Rozšírenie | 1 024 | 512 tokenov | Samostatný checkpoint s inštrukciou pre otázku. |
| [Qwen/Qwen3-Embedding-4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B) | Rozšírenie | 2 560 | 32 768 tokenov | Či väčší Qwen prinesie zlepšenie primerané nákladom. |
| [Qwen/Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B) | Rozšírenie | 4 096 | 32 768 tokenov | Ďalší bod porovnania veľkosti modelu, ak bude dostupný vhodný hardvér. |

Limity v tabuľke sú limity modelov, nie plánované nastavenie našich behov. Pred meraním pripneme presnú revíziu každého nového modelu.

**Férové porovnanie modelov:** pripravíme jednu spoločnú sadu textových chunkov, ktoré sa po pridaní metadát, prefixov a špeciálnych tokenov zmestia do limitu každého porovnávaného tokenizeru. Pri zahrnutí E5 musí každý taký vstup vyhovieť jeho limitu 512 tokenov. Všetky modely dostanú rovnaké textové úseky; text sa nesmie potichu orezať. Porovnanie pôvodného Qwen indexu s takto pripravenou sadou bude samostatný experiment s chunkovaním.

Použijeme modelom predpísané formátovanie: Qwen s inštrukciou na strane otázky, E5 base/large s prefixmi `query: ` a `passage: ` aj pri slovenčine, BGE-M3 bez Qwen inštrukcie. E5 large-instruct má vlastný vstupný formát. Formáty vychádzajú z príslušných modelových kariet vyššie. Zachováme odporúčaný pooling a normalizáciu; skóre rôznych modelov nebudeme považovať za vzájomne kalibrované.

Ďalšie embeddingové experimenty:

- **Jadro:** samotný text oproti textu s názvom dokumentu a cestou nadpisov.
- **Jadro:** dostupný akademický rok/platnosť v embeddingovom texte zapnuté a vypnuté; samostatne od filtrovania výsledkov.
- **Rozšírenie:** všeobecná anglická Qwen inštrukcia oproti súčasnej FIIT inštrukcii; bez inštrukcie ako kontrolný variant.
- **Rozšírenie:** rozmery Qwen3-0.6B `256 / 512 / 1 024`; po skrátení vektory znovu normalizovať. Qwen podporuje nastaviteľné výstupné rozmery podľa svojej [modelovej karty](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
- **Rozšírenie:** kvantizácia váh modelu a samostatne kvantizácia uložených vektorov. Sú to dve odlišné zmeny; pri oboch meriame stratu kvality aj úsporu.

## 3. Retrieval: ako získame kandidátov

| Metóda | Rozsah | Porovnanie a účel |
| --- | --- | --- |
| BM25 | Jadro | Lexikálny základ pre presné názvy, kódy predmetov, skratky a dátumy. |
| Dense retrieval | Jadro | Samostatné embeddingové vyhľadávanie pre každý model z jadra. |
| BM25 + dense cez RRF | Jadro | Spojenie lexikálneho a sémantického poradia bez priameho sčítania neporovnateľných skóre. |
| Hybrid + reranker | Jadro | Vyhľadanie širšej množiny a jej preusporiadanie podľa otázky. |
| Vážená kombinácia skóre | Rozšírenie | Porovnanie s RRF; skóre najprv normalizovať a váhu ladiť iba na dev. |
| MMR | Rozšírenie | Vplyv diverzity výsledkov na duplicity a pokrytie viacerých podkladov. |
| BGE-M3 sparse | Rozšírenie | Naučené lexikálne váhy oproti BM25. |
| BGE-M3 dense + sparse | Rozšírenie | Hybrid v rámci jedného modelu. |
| BGE-M3 multi-vector / kombinovaný režim | Rozšírenie | Či jemnejšie porovnávanie textu stojí za väčší index a latenciu. |

BM25 budeme vyhodnocovať na rovnakých chunkoch ako dense retrieval. Východisko: `k1 = 1,2`, `b = 0,75`; obmedzené ladenie na dev môže skúsiť `k1 ∈ {0,9; 1,2; 1,5}` a `b ∈ {0,4; 0,75}`. Pravidlá tokenizácie a zachovania kódov predmetov uložíme do konfigurácie. Definícia a parametre: [Okapi BM25](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html).

Pre RRF začneme konštantou `c = 60`, voliteľne porovnáme `20 / 60 / 100`. Skóre kandidáta bude `sum(1 / (c + rank))` cez zoznamy, v ktorých sa nachádza; poradie počítame od 1. Princíp: [pôvodná práca o Reciprocal Rank Fusion](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf).

Rozlíšime dva parametre:

- **Počet kandidátov:** `20 / 50 / 100` z každej retrieval vetvy. Pri hybride ich zjednotíme podľa ID a uložíme skutočnú veľkosť množiny; dve vetvy po 50 môžu dať až 100 kandidátov.
- **Počet výsledkov:** kvalitu meriame pri `k = 1 / 3 / 5 / 10`. Počet úryvkov odovzdaných generátoru navyše obmedzí tokenový rozpočet kontextu.

Najprv použijeme presné vyhľadávanie cez NumPy, aby aproximácia nevnášala ďalšiu premennú. FAISS/HNSW alebo vektorovú databázu zaradíme len ako rozšírenie pre výkon a škálovanie; budeme merať aj zhodu s presnými najbližšími susedmi.

## 4. Reranking: ako zoradíme kandidátov

Reranker dostane otázku a kandidátsky úryvok. Hodnotíme, či zlepší poradie už nájdených dôkazov; nevie zachrániť dôkaz, ktorý v množine kandidátov vôbec nie je.

| Variant | Rozsah | Čo porovnáme |
| --- | --- | --- |
| Bez rerankingu | Jadro; kontrolný variant | Pôvodné dense alebo hybridné poradie. |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Jadro | Viacjazyčný model hodnotiaci dvojicu otázka–úryvok. |
| [Qwen/Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | Jadro | Alternatívny reranker s inštrukciou a vlastným spôsobom skórovania. |
| [Qwen/Qwen3-Reranker-4B](https://huggingface.co/Qwen/Qwen3-Reranker-4B) | Rozšírenie | Vplyv veľkosti rerankera. |
| [Qwen/Qwen3-Reranker-8B](https://huggingface.co/Qwen/Qwen3-Reranker-8B) | Rozšírenie | Ďalšie porovnanie pri dostupnom hardvéri. |

Pre porovnanie rerankerov zmrazíme tú istú množinu kandidátov a ten istý text. Dĺžku dvojice overíme konkrétnym tokenizerom vrátane otázky a formátovania. Príliš dlhý úryvok rozdelíme na spoločné okná a vopred stanovíme agregáciu, napríklad maximum skóre okien; nesmie dôjsť k nezaznamenanému orezaniu. Následne môžeme samostatne porovnať dlhšie vstupy podporované daným modelom.

Budeme merať kvalitu pred a po rerankingu, pokrytie dôkazov v kandidátoch a pridanú latenciu. Kandidátne množiny `20 / 50 / 100` nebudeme zamieňať s finálnym top-k.

## 5. Chunkovanie a zostavenie textu

| Variant | Rozsah | Čo sa mení |
| --- | --- | --- |
| Súčasný block-aware + token-aware | Jadro; existujúci základ | Celé bloky, tabuľky a následná kontrola tokenového limitu. |
| Pevné tokenové okná | Jadro | Jednoduchý základ s presnou veľkosťou a voliteľným prekrytím. |
| Rekurzívne delenie | Jadro | Preferované hranice nadpis → odsek → veta → tokenový limit. |
| Parent–child retrieval | Rozšírenie | Vyhľadávať malé úryvky, ale do odpovede doplniť väčší nadradený úsek. |
| Semantic chunking | Rozšírenie | Hranice podľa zmien témy; započítať dodatočné embeddingy a čas. |
| Kontext doplnený modelom pred indexovaním | Rozšírenie | Krátky opis pôvodu úryvku; pôvodný text a generovaný opis uchovať oddelene. |

Parametre budeme meniť postupne:

- Cieľové veľkosti `256 / 512 / 1 024 / 2 048` tokenov tam, kde ich model a hardvér podporujú. Rozpočet zahŕňa pridaný kontext; pri E5 platí celkový limit 512.
- Overlap `0 % / 10 % / 20 %` pri oknách a rekurzívnom delení. Pri tabuľkách neopakovať náhodné úseky; opakovať hlavičku a potrebný kontext.
- Pridávanie názvu, nadpisov a časových metadát overiť oddelene od zmeny veľkosti.
- Tabuľka ako celý blok oproti deleniu po riadkoch s opakovanými hlavičkami a kontextom. Sledovať väzby predmet–kredit, udalosť–dátum a význam zlúčených buniek.
- Rozšírenie o susedný úryvok alebo rodiča hodnotiť aj podľa tokenov navyše a podielu nerelevantného kontextu.

Na porovnanie metód delenia použijeme rovnaký zdrojový korpus, embeddingový model, retrieval a otázky. Počet chunkov, priemernú/skutočnú maximálnu dĺžku, duplicitu textu a veľkosť indexu uložíme ako výsledok experimentu.

**Dôležité pre hodnotenie:** nové chunkovanie mení ID a hranice dôkazov. Referencie treba premapovať cez dokument, stranu a presný zdrojový úsek, pričom sa zachovajú alternatívy v `support_sets`. Samotná zhoda dokumentu nestačí. Pri delení pôvodného chunku treba overiť, či vybrané dieťa skutočne obsahuje potrebný dôkaz; zásah ľubovoľnej časti rodiča môže skóre nadhodnotiť.

## 6. Metadáta, časová platnosť a duplicity

| Experiment | Varianty | Na čo sa zameriame |
| --- | --- | --- |
| Akademický rok | Bez obmedzenia / tvrdý filter / mäkké zvýhodnenie | Zámena aktuálneho a historického katalógu alebo harmonogramu. |
| Neznámy rok zdroja | Zachovať ako fallback / vyradiť pri explicitnom roku | Pokles pokrytia oproti riziku nesprávneho obdobia. |
| Typ dokumentu | Bez preferencie / zvýhodnenie typu podľa otázky | Katalóg predmetov, harmonogram, prijímacie podmienky. |
| Duplicity výsledkov | Pôvodné poradie / zjednotenie aliasov / obmedzenie podobných výsledkov | Či viac vydaní alebo kópií vytláča ďalšie potrebné dôkazy. |
| Platnosť a rozpory | Bez osobitného pravidla / explicitná kontrola obdobia a konfliktov | Či odpoveď cituje podklad pre požadované obdobie. |

Časové filtrovanie a deduplikácia patria do jadra; zložitejšie preferencie a detekcia rozporov sú rozšírenie. Rok odvodzujeme z otázky a dostupných zdrojových metadát, nie zo skrytej referenčnej anotácie. Dokument uvádzajúci viac rokov nemusí platiť pre všetky uvedené obdobia. Staršie vydania automaticky neodstraňujeme, pretože sú potrebné pre historické otázky.

Otázka bez roka nemusí znamenať „najnovší dokument“. Ak odpoveď závisí od obdobia, variant s upresnením má vyžiadať rok. Relatívne slová ako „teraz“ posudzujeme voči uloženému snapshotu; dátum experimentu nepotvrdzuje aktuálnosť zdroja.

## 7. Úprava a rozširovanie otázky

| Postup | Rozsah | Porovnanie |
| --- | --- | --- |
| Pôvodná otázka | Jadro; kontrolný variant | Bez prepisovania významu. |
| Normalizácia zápisu | Jadro | Unicode, medzery, zjednotenie `2025/26` a `2025/2026`; zachovať pôvodnú otázku. |
| Rozšírenie skratiek | Jadro | Overený slovník typu BP/BP2, DBS, AIS; pôvodný výraz ponechať a doplniť názov, ak je jednoznačný. |
| Tolerancia chýbajúcej diakritiky | Jadro | Pôvodný text oproti doplnkovej normalizovanej lexikálnej vetve; merať aj stratu presných zhôd. |
| LLM query rewriting | Rozšírenie | Hovorová otázka → vyhľadávacia formulácia bez doplnenia nových faktov. |
| Multi-query | Rozšírenie | Pôvodná otázka + najviac 3 varianty, výsledky zlúčené cez RRF. |
| Rozklad otázky | Rozšírenie | Viac podotázok pre porovnania a otázky vyžadujúce viac zdrojov. |
| HyDE | Rozšírenie | Embedding hypotetickej odpovede oproti embeddingu pôvodnej otázky. |

HyDE vychádza z práce [Precise Zero-Shot Dense Retrieval without Relevance Labels](https://arxiv.org/abs/2212.10496). Hypotetický text používame len na vyhľadanie; nepovažujeme ho za dôkaz ani citovaný zdroj.

Slovník skratiek pripravíme z korpusu a dev príkladov. Pri LLM úpravách uložíme presný prompt, model, výstup, seed a dodatočný čas. Zakážeme dopĺňať rok, konkrétny termín alebo odpoveď, ktoré v otázke nie sú. Robustnosť preveríme na pároch s diakritikou/bez nej, preklepmi a hovorovým zápisom; odvodené varianty zostanú v rovnakom splite ako pôvodná otázka.

## 8. Modely na generovanie odpovedí

Táto etapa nasleduje po vyhodnotení retrievalu. Pri hlavnom porovnaní generátorov zmrazíme vyhľadané podklady, ich poradie a rovnaký text kontextu, ktorý sa zmestí do každého použitého modelu.

| Model – presný identifikátor a dokumentácia | Rozsah | Čo porovnáme |
| --- | --- | --- |
| [Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | Jadro | Menší generátor slovenských odpovedí s citáciami. |
| [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) | Jadro | Iná rodina pri podobnej veľkosti; v tomto porovnaní len textový vstup. |
| [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | Rozšírenie | Vplyv veľkosti generátora v rovnakej rodine. |
| [mistralai/Mistral-Nemo-Instruct-2407](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407) | Rozšírenie | Ďalší viacjazyčný generátor, ak to dovolia výpočtové náklady. |

Pri Qwen začneme s vypnutým thinking režimom; jeho zapnutie bude prípadné samostatné porovnanie s vlastným rozpočtom a meraním celkovej latencie. Prepínač opisuje [modelová karta Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B). Presný checkpoint, chat template, runtime a kvantizáciu zaznamenáme pre každý model.

Experimenty s generovaním a kontextom:

| Faktor | Plánované varianty |
| --- | --- |
| Dostupnosť podkladov | Bez retrievalu / reálny retrieval / referenčné dôkazy ako diagnostický „oracle“ variant. Oracle nie je nasaditeľný systém a vykazuje sa osobitne. |
| Prompt | Základný prompt / explicitné pravidlá pre oporu tvrdení, citácie, obdobie a nedostatok informácií. |
| Počet úryvkov | `3 / 5 / 10`, vždy spolu s uvedením skutočného množstva textu a tokenov. |
| Rozpočet podkladov | `2 048 / 4 096 / 8 192` tokenov, ak sa celý vstup aj rezerva na výstup zmestia do zvoleného runtime limitu. |
| Deduplikácia a poradie | Retrieval poradie / odstránené opakovania; alternatívne poradie až ako rozšírenie. |
| Formát citácií | Označenie podkladu `[S1]` a mapovanie na URL, dokument a stranu; kontrolovať aj obsahovú správnosť citácie. |
| Nedostatok podkladov | Vynútená odpoveď ako kontrolný variant / upresnenie alebo priznanie chýbajúceho podkladu. |
| Dekódovanie | Východiskovo pevné nastavenie, napr. `do_sample=False`, limit 512 nových tokenov; pri skúšaní samplovania uviesť parametre a opakovať behy so seedmi. |

Zmeny promptu, top-k a rozpočtu budeme robiť oddelene. Pri porovnaní modelov dostanú modely rovnaký text; samostatné ladenie rozpočtu konkrétnemu tokenizeru už označíme ako porovnanie celých konfigurácií. Citácie a metadáta musia zostať zachované aj pri skrátení kontextu. Nezmestené úryvky vynecháme podľa vopred určenej politiky a výber uložíme.

Rozhodnutie odpovedať, upresniť alebo odmietnuť nepodloženú odpoveď budeme porovnávať s prahom ladeným na dev. Kosínusové ani rerankingové skóre nie je pravdepodobnosť správnosti; jeden spoločný prah pre všetky modely nemá automaticky rovnaký význam. Dokumenty v kontexte sú podklady, nie pokyny pre asistenta; toto správanie overíme aj na kontrolných príkladoch s vloženým pokynom.

## 9. Kvalita vstupných dát a extrakcie

Retrieval môže zlyhať už preto, že sa správny fakt stratil pri parsovaní. Na ručne skontrolovanej vzorke pripravíme tieto porovnania:

- **Jadro:** zachovanie štruktúry tabuliek oproti obyčajnému textovému exportu; overiť párovanie hodnôt a popisov.
- **Jadro:** názvy, nadpisy, URL a čísla strán; overiť, že citácia vedie na skutočný podklad.
- **Rozšírenie:** generický PDF parser oproti existujúcemu profilu harmonogramu na dokumentoch, pre ktoré je profil určený.
- **Rozšírenie:** natívna textová vrstva oproti OCR na kontrolovanej vzorke; vyhodnotiť stratené fakty, dátumy a poradie stĺpcov.
- **Rozšírenie:** ready korpus oproti korpusu doplnenému o **ručne schválenú** vzorku review/OCR segmentov. Neupravený review obsah nezaradiť automaticky.
- **Rozšírenie:** odstránenie opakovaných hlavičiek, pätičiek a obsahových duplicít; historické vydania zachovať samostatne.

Pri porovnaní extrakcie držíme zdrojové súbory rovnaké. Meriame zachovanie vybraných faktov a vzťahov, chyby citácií a následný vplyv na retrieval. Pri OCR možno doplniť CER/WER až po príprave ručného prepisu. Po pridaní review dokumentov treba doplniť aj referenčné dôkazy; aktuálny benchmark hodnotí iba vybrané ready zdroje.

## 10. Dataset, metriky a pravidlá vyhodnotenia

Použijeme [FIIT QA dataset](../evaluation/fiit_qa/README.md):

| Split | Zodpovedateľné | Vyžadujú upresnenie | Nezodpovedateľné | Spolu |
| --- | ---: | ---: | ---: | ---: |
| dev | 25 | 3 | 2 | 30 |
| test | 75 | 7 | 8 | 90 |
| Spolu | 100 | 10 | 10 | 120 |

Na dev vyberáme varianty a parametre. Pred záverečným testom uzamkneme konfigurácie aj pravidlá hodnotenia; test nepoužijeme na ďalšie ladenie. Anotácie zatiaľ nemajú nezávislú odbornú kontrolu. Dôkazy pokrývajú iba 19 dokumentov a rozdelenie nie je oddelené podľa celých dokumentov, preto výsledky opisujú tento benchmark, nie všeobecnú kvalitu na celom webe FIIT.

### Metriky dostupné v projekte

Existujúci [vyhodnocovač](../tools/evaluate_qa_retrieval.py) počíta:

| Metrika | Význam |
| --- | --- |
| `known_evidence_hit@k` | Podiel zodpovedateľných otázok, pri ktorých sa našiel aspoň jeden známy dôkaz. |
| `mrr@k` | Priemerná prevrátená pozícia prvého známeho dôkazu, s nulou pri nenájdení v top-k. |
| `evidence_coverage@k` | Priemerný podiel pokrytých potrebných množín dôkazov. |
| `complete_support@k` | Podiel otázok, pre ktoré sú pokryté všetky potrebné množiny dôkazov. |
| `answerability_accuracy` | Presnosť troch tried správania, ak systém dodá tieto predikcie. |

Retrieval metriky počítame iba zo zodpovedateľných otázok; správanie na všetkých otázkach splitu. Pre jednu potrebnú množinu stačí ľubovoľný uvedený alternatívny dôkaz, ale pri viacerých množinách treba pokryť každú. Chýbajúce retrieval predikcie sa rátajú ako neúspech.

Pri súčasnom token-aware indexe vyhodnocovač očakáva pôvodné `parent_chunk_id`: opakovaného rodiča ponecháme iba raz, pri prvom výskyte. Na získanie top-k unikátnych rodičov môže byť potrebné vyhľadať viac než k detí. Popri tejto existujúcej metrike overíme aj prítomnosť skutočného dôkazu vo vybranom texte. Pri novom chunkovaní je potrebné premapovanie referencií z časti 5, nie len dosadenie nových ID.

Známe dôkazy nie sú úplné anotácie všetkých relevantných chunkov. Tieto metriky preto nebudeme označovať ako úplný recall alebo precision. nDCG, precision a úplný recall doplníme iba po príprave zodpovedajúcich relevance anotácií. Nenájdený anotovaný dôkaz môže mať aj inú správnu alternatívu; pri rozbore chýb ju treba skontrolovať.

### Hodnotenie, ktoré treba doplniť

- **Odpovede:** pokrytie `required_facts`, správnosť dátumov/čísel/rokov, výskyt `forbidden_claims`, podiel tvrdení podložených zdrojmi a správnosť citácií.
- **Správanie:** konfúzna matica troch tried, výsledky po triedach, podiel nesprávne zodpovedaných nezodpovedateľných otázok a zbytočných odmietnutí zodpovedateľných otázok.
- **Výkon:** čas embeddingu otázky, vyhľadávania, rerankingu, čas do prvého tokenu a celkový čas odpovede; p50/p95, využitie RAM/VRAM, čas vytvorenia a veľkosť indexu.
- **Rozbor skupín:** tabuľky/predmety, termíny, explicitný rok, skratky, chýbajúca diakritika, otázky s viacerými zdrojmi a nesprávnym predpokladom; vždy uviesť počet otázok v skupine.
- **Neistota výsledkov:** uvádzať aj absolútne počty úspechov. Pri intervaloch alebo párovom bootstrap porovnaní zohľadniť skupiny prepojených dôkazov; otázky nad rovnakým zdrojom nie sú plne nezávislé.

Výsledné odpovede hlavného porovnania skontrolujeme podľa rovnakej rubriky bez zobrazenia názvu modelu hodnotiteľovi. Automatický LLM hodnotiteľ môže byť doplnok; jeho verdikt overíme na ručne hodnotenej vzorke a uložíme jeho model, verziu a prompt. Existujúci retrieval skript text odpovede ani citácie nehodnotí.

## 11. Poradie experimentov a výber výslednej konfigurácie

| Etapa | ID | Čo vykonáme | Čo počas porovnania nemeníme |
| --- | --- | --- | --- |
| 1 | E00 | Validácia dát, zmrazenie snapshotu a referencií; meranie súčasného Qwen retrievalu. | Súčasná konfigurácia. |
| 2 | E01 | Qwen0.6B / BGE-M3 / E5-base / E5-large na spoločných chunkoch. | Texty chunkov, otázky, metadáta, dense retrieval, k. |
| 3 | E02 | BM25 / zvolený dense / hybrid RRF. | Spoločné chunky, otázky a vybraný embedding. |
| 4 | E03 | Bez rerankera / BGE reranker / Qwen0.6B reranker. | Kandidáti, ich text a finálne k. |
| 5 | E04 | Block-aware / pevné okná / rekurzívne delenie; potom vybrané veľkosti a overlap. | Zdrojové dokumenty, modely, retrieval a referencia na zdrojové úseky. |
| 6 | E05 | Metadáta v texte, rok, deduplikácia a rozšírenie skratiek, po jednej zmene. | Ostatné nastavenia zvolenej konfigurácie. |
| 7 | E06 | Zostavenie kombinovanej konfigurácie a kontrola interakcií úprav na dev. | Dataset a vopred zvolené metriky. |
| 8 | E07 | Qwen3-4B / Gemma3-4B s rovnakými uloženými podkladmi. | Retrieval, kontext, obsah pravidiel a hodnotiaca rubrika. |
| 9 | E08 | Ladenie kontextu, promptu a správania pri chýbajúcich podkladoch na dev. | Zvolený generátor, vždy len jeden menený faktor. |
| 10 | E09 | Finálne porovnanie uzamknutých konfigurácií na test. | Všetky parametre a pravidlá hodnotenia. |
| 11 | E10+ | Vybrané rozšírenia: väčšie modely, multi-query, HyDE, parent–child, BGE sparse/multi-vector. | Pre každé vopred určený kontrolný variant; pri ďalšom ladení nový oddelený finálny test. |

Primárne kritérium pri výbere retrievalu na dev bude **`complete_support@5`**, následne **`mrr@5`**; pri porovnateľnej kvalite uprednostníme nižšiu latenciu a pamäťové nároky. Zároveň skontrolujeme otázky s viacerými podkladmi a správne obdobie. Pri generovaní rozhoduje vecná správnosť a opora v zdrojoch vrátane správneho upresnenia/odmietnutia, potom rýchlosť. Malé rozdiely na 25 zodpovedateľných dev otázkach nebudeme vydávať za spoľahlivý dôkaz prevahy.

Do finálneho retrieval porovnania ponecháme BM25, pôvodný Qwen základ, najlepší samostatný dense variant, hybrid a zvolený hybrid s rerankingom. Pre kombinovanú konfiguráciu doplníme **ablácie**: odobrať po jednej použitú úpravu, napríklad filter roka, reranker či rozšírenie skratiek. Tak zistíme, ktoré časti prispievajú k výsledku aj v kombinácii.

## 12. Hardvér a reprodukovateľnosť

Existujúca embeddingová konfigurácia cieli na Windows, Python 3.13 a GTX 1080 Ti a používa FP32; podrobnosti sú v [embeddingovom README](../embeddings/README.md). Podporu nového modelu, backendu, presnosti a kvantizácie najprv overíme krátkym skúšobným behom. To, že model podporuje dlhý kontext, neznamená, že ho zvládne naša karta pri zvolenej dávke.

Pre 4B/8B a väčšie modely zvážime podporovanú kvantizáciu, CPU offload alebo iný dostupný hardvér. Pamäť váh nie je celá spotreba: treba zahrnúť aktivácie, kontext a pri generovaní KV cache. Nepredpokladáme, že všetky modely budú naraz v GPU pamäti. Pri sekvenčnom načítavaní zaznamenáme aj jeho vplyv na odozvu systému.

Latenciu porovnávame na rovnakom hardvéri, s oddeleným načítaním modelu a zahriatymi opakovanými otázkami. Výsledky z iných zariadení vykážeme oddelene. Pri kvantizovaných generátoroch uvedieme presný formát a revíziu súboru; rozdiel modelov s odlišnou kvantizáciou nebudeme vysvetľovať iba architektúrou. Latenciu meriame v režime zodpovedajúcom reálnej otázke, nie len veľkej dávke benchmarku.

Pravidlá evidencie, šablóny a prepojenie zistení na tvrdenia v práci sú v
[experimentálnom zápisníku](../experiments/README.md) a jeho
[pracovnom postupe](../experiments/WORKFLOW.md). Do Gitu patria stručné plány,
zistenia a malé reprodukčné balíky v `experiments/`; úplné výstupy zostávajú
v ignorovanom `output/experiments/` s overenou záložnou kópiou. Ignorovanie
v Gite samo osebe nie je zálohovanie. Súhrny metrík v Gite musia odkazovať na
konkrétny beh a zachovať pôvod a spôsob prípadného výberu z úplného výstupu.

Pre každý beh navrhujeme samostatný priečinok `output/experiments/<run_id>/` s týmito artefaktmi:

| Súbor | Čo uložíme |
| --- | --- |
| `config.json` | ID experimentu, menený faktor, parametre chunkovania, model/revízia, prefixy, metadáta, retrieval, fusion, reranking, filtre, kontext a generovanie. |
| `manifest.json` | Verzia kódu, odtlačok zmien pri nečistom pracovnom strome, SHA-256 korpusu/datasetu/chunkov, revízie modelov, prostredie, hardvér, presnosť, kvantizácia a seedy. |
| `retrieval.jsonl` | ID otázky, zoradení kandidáti a finálne ID, pôvodné aj nové ID, skóre vetiev, vyradenie filtrami a časovanie. |
| `predictions.jsonl` | Export v schéme existujúceho vyhodnocovača; po príslušnom mapovaní a deduplikácii. |
| `answers.jsonl` | Skutočný kontext a prompt, odpoveď, citácie, predikcia správania, tokeny a časy. |
| `metrics.json` | Súhrnné metriky, rozpis podľa skupín a jednotlivých otázok. |
| `errors.md` | Konkrétne zlyhania: extrakcia, chunkovanie, nesprávny rok, retrieval, reranking, generovanie alebo referencia. |

Ide o navrhované artefakty budúceho runnera, nie o súbory, ktoré už aktuálne príkazy automaticky vytvárajú. Hotový výsledok zahŕňa vlastný konverzačný RAG, reprodukovateľné porovnanie modelov a retrievalu, finálnu konfiguráciu s abláciami a hodnotenie odpovedí aj dialógov na verejných datasetoch a realistických scenároch. Analýza agentic RAG patrí do S00. Fine-tuning, GraphRAG, ďalšie backendy a agentný prototyp sú rozšírenia podľa návrhu, zistených chýb a dostupných zdrojov.

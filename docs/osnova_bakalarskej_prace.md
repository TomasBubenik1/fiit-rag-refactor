# Osnova bakalárskej práce o vyhľadávaní v dokumentoch FIIT

Sprievodca písaním kapitol a prípravou experimentov

Tvoja práca môže sledovať jednu konkrétnu otázku: ako pripraviť rôznorodé dokumenty fakulty tak, aby systém dokázal k študentskej otázke nájsť správny podklad a ukázať jeho zdroj. Každá kapitola potom vysvetlí jednu časť riešenia, jej dôvody a spôsob overenia.

## Zameranie a hlavná myšlienka práce

**Pracovný návrh názvu:** Vyhľadávanie informácií v dokumentoch FIIT STU pomocou jazykových modelov.

Ak bude výsledkom aj generovanie odpovedí, môžeš použiť presnejší názov: **Systém na odpovedanie na otázky o štúdiu na FIIT STU s využitím RAG**. RAG znamená Retrieval Augmented Generation, teda generovanie odpovede s využitím vyhľadaných podkladov [1].

**Návrh cieľa do úvodu:** Cieľom práce je navrhnúť, implementovať a vyhodnotiť postup spracovania fakultných dokumentov a vyhľadávania relevantných informácií pre otázky študentov. Riešenie sa zameriava na zachovanie štruktúry dokumentov, dohľadateľnosť zdrojov a rozlíšenie informácií podľa obdobia ich platnosti.

Ak doplníš generovanie, pridaj samostatný cieľ: vytvárať odpovede podložené nájdenými úryvkami a overiť ich vecnú správnosť aj správnosť citácií. Samotné vektorové vyhľadávanie tvorí vyhľadávaciu časť RAG; celý systém potrebuje aj generovanie odpovede.

**Možný vlastný prínos:** overený postup prípravy slovenských fakultných dokumentov, zachovanie tabuliek a zdrojových údajov pri delení textu a experimentálne porovnanie zvolených variantov vyhľadávania. Prínos presne pomenuj až podľa uskutočnených experimentov.

## Prehľad navrhovanej osnovy

Nasledujúci rozsah je pomôcka na rozdelenie približne 40 strán hlavného textu. Nie je to záväzný predpis rozsahu práce.

| Kapitola | Čo má čitateľ pochopiť | Orientačne strán |
| --- | --- | --- |
| 1 Úvod | Aký problém riešiš a čo je cieľom | 2 |
| 2 Teoretické východiská a súvisiace práce | Na akých princípoch riešenie stojí | 8 |
| 3 Analýza problému a vstupných dát | Aké dáta máš a čo od systému potrebuješ | 5 |
| 4 Návrh riešenia | Ako sú časti prepojené a prečo | 6 |
| 5 Implementácia | Ako si návrh uskutočnil | 7 |
| 6 Experimenty a vyhodnotenie | Čo funguje podľa meraní | 8 |
| 7 Diskusia | Čo výsledky znamenajú a kde sú hranice | 2 |
| 8 Záver | Čo sa podarilo a čo zostáva otvorené | 2 |

Literatúra a prílohy sú samostatné časti. Abstrakt, kľúčové slová a ďalšie úvodné náležitosti priprav podľa fakultnej šablóny. Číslovanie podkapitol si doplň podľa nej; nižšie uvedené podnadpisy môžeš priamo použiť ako ich názvy.

## 1 Úvod

**Úloha kapitoly:** vysvetliť, prečo má tento konkrétny problém zmysel riešiť a podľa čoho posúdiš splnenie cieľa.

### Motivácia a opis problému

Opíš situáciu študenta, ktorý potrebuje nájsť termín, podmienku absolvovania predmetu alebo pravidlo štúdia. Informácia môže byť na webovej stránke, v tabuľke PDF či v dokumente pre iný akademický rok. Ako konkrétny príklad použi otázku „Kedy sa začína letný semester 2025/2026?“ a vysvetli, prečo musí systém nájsť príslušný harmonogram.

Všeobecné tvrdenia o správaní študentov podlož zdrojom alebo vlastným prieskumom. Motivačný príklad môžeš uviesť aj bez prieskumu, ak ho tak označíš.

### Cieľ práce a čiastkové ciele

Rozdeľ cieľ na overiteľné kroky: analyzovať korpus, pripraviť jednotnú reprezentáciu dokumentov, navrhnúť delenie textu, vytvoriť vyhľadávanie a vyhodnotiť ho na otázkach. Ak robíš chatbota, pridaj tvorbu odpovedí so zdrojmi a ich samostatné hodnotenie.

### Výskumné otázky a štruktúra práce

Vyber si dve alebo tri otázky, napríklad:

- Ako ovplyvní zachovanie štruktúry tabuliek úspešnosť vyhľadávania údajov o predmetoch?
- Ako sa pri rovnakom korpuse líši vyhľadávanie podľa kľúčových slov a pomocou embeddingov?
- Pomôže filtrovanie podľa akademického roka pri otázkach s určeným obdobím?

Potom jedným krátkym odsekom predstav usporiadanie kapitol. Úvod môžeš začať písať hneď, ale jeho finálnu verziu uprav podľa skutočných výsledkov.

## 2 Teoretické východiská a súvisiace práce

**Úloha kapitoly:** vysvetliť pojmy potrebné na pochopenie tvojich rozhodnutí. Každú časť prepoj s tým, kde ju využiješ v návrhu. Základný odborný rámec nájdeš v zdrojoch [1] až [5].

### Jazykové modely a odpovedanie na otázky

Vysvetli, čo jazykový model dostáva na vstupe a čo vytvára na výstupe. Rozober problém nepodložených odpovedí a potrebu pracovať s konkrétnymi dokumentmi. Vysvetli rozdiel medzi použitím predtrénovaného modelu, jeho dotrénovaním a doplnením vyhľadaného kontextu. Rozsah technického opisu prispôsob tomu, čo v práci reálne používaš.

### Princíp RAG

Opíš postup od otázky cez vyhľadanie úryvkov po odpoveď so zdrojmi. Oddeľ prípravu korpusu od spracovania otázky počas používania systému. Nakresli jednoduchú schému a vysvetli, že chyba môže vzniknúť pri extrakcii, vyhľadávaní aj generovaní [1].

### Reprezentácia textu a vyhľadávanie

Predstav vyhľadávanie podľa kľúčových slov, napríklad BM25, a vyhľadávanie pomocou hustých vektorových reprezentácií. Embedding vysvetli ako číselnú reprezentáciu textu používanú na porovnanie otázky a úryvku. Doplň význam kosínusovej podobnosti a výberu top k výsledkov [2, 5].

Hybridné vyhľadávanie, rozširovanie skratiek a preusporiadanie výsledkov pomocou ďalšieho modelu predstav ako možné rozšírenia. Ak ich neimplementuješ, jasne ich odlíš od vlastného riešenia. Pri Qwen3 vysvetli použitie modelu na reprezentáciu textu; nevydávaj embeddingový model za generátor odpovedí [3, 4].

### Predspracovanie a delenie dokumentov

Vysvetli rozdiel medzi HTML, textovým PDF a skenom vyžadujúcim OCR. Rozober, prečo pri extrakcii záleží na nadpisoch, stĺpcoch, tabuľkách a priradení hodnoty k jej názvu. Pri delení porovnaj pevné dĺžky a hranice obsahových blokov. Vysvetli aj rozdiel medzi počtom znakov a tokenov.

### Hodnotenie a súvisiace riešenia

Predstav testovaciu otázku, referenčný zdroj a metriku. Vyber niekoľko prác o RAG, vyhľadávaní alebo podobnom univerzitnom systéme a porovnaj ich dáta, postup a hodnotenie. Pri každej vysvetli, čo preberáš a aký problém tvojho korpusu zostáva otvorený. Súvisiace práce majú viesť k vlastnému návrhu.

**Čo si pripraviť:** schému RAG a krátku porovnávaciu tabuľku vybraných prác. Odborné tvrdenia cituj; vlastné rozhodnutia zdôvodni zvlášť.

## 3 Analýza problému a vstupných dát

**Úloha kapitoly:** ukázať, s akými dátami pracuješ, čo je na nich náročné a aké požiadavky z toho vyplývajú.

### Používatelia a typy otázok

Vymedz cieľovú skupinu a podporované otázky. Môžu zahŕňať predmety, termíny, študijné pravidlá a kontakty. Rozlíš jednoduchú faktografickú otázku, otázku vyžadujúcu viac podkladov a nejednoznačnú otázku. Použi príklady z testovacej množiny, ale skontroluj, či sa na ne dá z korpusu odpovedať.

### Charakteristika korpusu

Opíš pôvod a spôsob získania dodaného balíka, zastúpené formáty, jazyk a časové obdobia. Rozlišuj počet vstupných súborov, normalizovaných dokumentov, strán PDF a výsledných úryvkov. Viaceré súbory môžu predstavovať rovnaký obsah alebo jeho odvodenú verziu.

Lokálny report `data/normalized/report.json` pri príprave tejto osnovy uvádza 2 214 normalizovaných dokumentov, 1 247 PDF dokumentov a 10 934 strán PDF. Uvádza tiež 9 580 úryvkov v skupine ready a 7 942 v skupine review. Ide o údaje uloženého behu, ktoré treba vo finálnej práci priradiť ku konkrétnej verzii dát. Stav ready znamená, že automatické kontroly nezistili problém s extrakciou; nezaručuje vecnú správnosť ani aktuálnosť.

### Problémy v dátach

Rozober duplicity, historické vydania, viacstĺpcové dokumenty, zlúčené bunky, OCR a chýbajúci obsah odkazov. Pri tabuľke vysvetli, čo by sa stalo, keby sa počet kreditov oddelil od názvu predmetu. Pri harmonograme ukáž riziko zámeny dátumu odovzdania a obhajoby práce.

### Požiadavky na riešenie

Odvoď požiadavky z konkrétnych problémov: zachovať URL a číslo strany, udržať súvislosti v tabuľke, evidovať dostupné časové údaje a oddeliť obsah vyžadujúci kontrolu. Doplň reprodukovateľnosť spracovania a primeranú odozvu. Ak bude súčasťou generovanie, stanov správanie pri chýbajúcom alebo rozpornom podklade.

**Čo si pripraviť:** tabuľku zloženia korpusu a tri ukážky problémového vstupu spolu s požadovaným výstupom.

## 4 Návrh riešenia

**Úloha kapitoly:** vysvetliť architektúru a dôvody rozhodnutí skôr, než začneš opisovať konkrétny kód.

### Architektúra a tok dát

Navrhni dve vetvy. Príprava dát vedie od pôvodného dokumentu cez extrakciu a normalizáciu k úryvkom a indexu. Spracovanie otázky vedie od otázky cez jej reprezentáciu k vyhľadaniu relevantných úryvkov. Pri celom RAG doplň zostavenie kontextu a generovanie odpovede.

### Jednotná reprezentácia a dohľadateľnosť zdrojov

Vysvetli, ktoré údaje nesie dokument a ktoré úryvok: identifikátor, názov, text, zdroj, strana, nadpisový kontext, príznaky kvality a dostupné údaje o platnosti. Ukáž jeden skrátený záznam a vysvetli, ako sa od výsledku vyhľadávania dostaneš k pôvodnému dokumentu.

### Delenie textu a tvorba indexu

Zdôvodni zachovanie obsahových blokov a samostatnú kontrolu tokenového rozpočtu pred vytvorením embeddingu. Opíš, ako sa pri rozdelení veľkej tabuľky zachovajú hlavičky a pôvod úryvku. Vysvetli výber embeddingového modelu, podobnostnej funkcie a lokálneho uloženia indexu. Výber opieraj aj o hardvér a potreby slovenčiny; vlastnú kvalitu musí potvrdiť experiment.

### Vyhľadávanie a časová platnosť

Opíš výber top k úryvkov a prácu s metadátami. Rozlišuj podobnosť otázky s textom od splnenia podmienky akademického roka. Ak navrhneš filter, urči aj postup pri chýbajúcom roku, viacerých rokoch v dokumente a otázke bez časového určenia. Implementované a iba navrhované správanie od seba oddeľ.

### Generovanie odpovede pri rozšírení na celý RAG

Stanov formát kontextu, citácií a odpovede pri nedostatku informácií. Dokumenty odovzdávané modelu považuj za podklady; navrhni, ako zabrániš tomu, aby ich prípadné vložené pokyny menili pravidlá asistenta. Túto podkapitolu ponechaj iba v rozsahu skutočne navrhnutej alebo realizovanej časti práce.

**Čo si pripraviť:** diagram architektúry, ukážku dátového záznamu a prehľad parametrov, ktoré neskôr porovnáš.

## 5 Implementácia

**Úloha kapitoly:** ukázať, ako si návrh uskutočnil, vrátane náročných miest a spôsobu kontroly. Sústreď sa na rozhodnutia, ktoré ovplyvňujú výsledok.

### Extrakcia a normalizácia

Opíš získanie hlavného obsahu HTML, odstránenie navigácie a zachovanie nadpisov, odkazov a tabuliek. Pri PDF vysvetli získanie textu, použitie OCR, rozpoznanie tabuliek a evidovanie neistých výsledkov. Ukáž jeden príklad vstupu a výstupu. Následne vysvetli zjednotenie formátov, priradenie zdrojov, duplicít a stavov kontroly.

### Delenie textu a embeddingy

V aktuálnom kóde má blokové delenie mäkký cieľ 2 400 znakov a zachováva celé bloky. Následné delenie pred embeddingom kontroluje skutočný počet tokenov vrátane pridaného kontextu. Vysvetli, prečo sú to dve rôzne obmedzenia a čo sa stane s nadmerne veľkým blokom.

Projekt používa `Qwen/Qwen3-Embedding-0.6B`. Pri opise implementácie uveď použitú revíziu, konfiguráciu a hardvér. Dokumentovaný predvolený rozpočet je 2 048 tokenov na vstup; nejde o maximálny kontext modelu. Opíš aj uchovanie väzby na rodičovský úryvok a pokračovanie prerušeného vytvárania indexu.

### Vyhľadávanie a technické overenie

Vysvetli prevod otázky na vektor a porovnanie s normalizovanými vektormi dokumentov. Aktuálne vyhľadávanie používa NumPy a vracia úryvky so skóre a zdrojom. Skóre vysvetli ako mieru podobnosti. Nie je to pravdepodobnosť správnej odpovede.

Opíš kontroly zachovania zdrojov, tokenových limitov a tabuliek aj existujúce regresné testy. Uveď výsledok konkrétneho behu až po jeho vykonaní a uložení výstupu. Úspešný technický test sám osebe nepreukazuje kvalitu vyhľadávania.

### Prepojenie kapitol so súbormi projektu

| Oblasť | Podklady v projekte |
| --- | --- |
| HTML a PDF extrakcia | `tools/extract_main_content.py`, `tools/parse_pdf.py`, `tools/parse_harmonogram_pdf.py` |
| Normalizácia korpusu | `tools/normalize_dataset.py`, `tools/batch_dataset_pdfs.py` |
| Delenie textu | `chunking/block_aware.py`, `chunking/token_aware.py` |
| Embeddingy a index | `embeddings/qwen3.py`, `tools/embed_chunks.py` |
| Vyhľadávanie a kontroly | `tools/search_embeddings.py`, `tools/validate_embeddings.py`, `tools/validate_normalized_dataset.py`, `tests/` |

Súbory sú oporou pri písaní. Hlavný text organizuj podľa riešených problémov; podrobné príkazy a dlhšie ukážky patria do príloh.

## 6 Experimenty a vyhodnotenie

**Úloha kapitoly:** odpovedať na výskumné otázky meraním. Oddeľ hodnotenie extrakcie, vyhľadávania a prípadného generovania.

### Testovacia množina a referenčné odpovede

Existujúca množina `data/eval_dataset.json` obsahuje 30 otázok. Použi ju ako východisko a skontroluj, či má každá otázka správny a dostupný referenčný zdroj. Pre presné hodnotenie doplň konkrétnu stranu alebo úryvok a požadovaný akademický rok. Pri otázke na aktuálne pravidlo nemusí byť staršie vydanie relevantné.

Normalizačný report uvádza 17 nevyriešených referencií z celkovo 63. Pred meraním ich skontroluj a oprav mapovanie alebo transparentne popíš vylúčenie. Pri hodnotení na úrovni dokumentov zjednoť opakované zásahy toho istého dokumentu. Inak môže viac úryvkov umelo zvyšovať niektoré metriky.

Otázky používané pri ladení oddeľ od záverečného testu. Pri malej množine popíš počet otázok v skupinách a obmedzenú možnosť zovšeobecnenia. Ak chceš spoľahlivo hodnotiť aj extrakciu, priprav ručne skontrolovanú vzorku dokumentov vrátane tabuliek a OCR.

### Porovnávané varianty

Začni základným embeddingovým vyhľadávaním. Vyber dve alebo tri porovnania, ktoré zodpovedajú cieľu a stihneš ich dôsledne overiť:

| Experiment | Čo zmeníš | Čo ponecháš rovnaké |
| --- | --- | --- |
| Spôsob vyhľadávania | BM25 oproti embeddingom | Korpus, otázky, referencia a hodnota k |
| Delenie textu | Pevná dĺžka oproti obsahovým blokom s tokenovým limitom | Model, zdrojové dokumenty a otázky |
| Časové filtrovanie | Bez filtra a s filtrom podľa roka | Model a otázky s určeným obdobím |
| Rozširovanie skratiek | Pôvodná otázka a otázka s rozvinutou skratkou | Index, model a otázky so skratkami |

Pri každom variante uveď presné nastavenia. Ak meníš viac vecí naraz, nebudeš vedieť určiť, čo spôsobilo rozdiel. Pri porovnaní delenia je vhodná aj referencia na úrovni dokumentu alebo odpovedného úseku, pretože identifikátory úryvkov sa medzi variantmi zmenia.

### Metriky a prevádzkové merania

Na začiatok stačí Hit Rate pri k rovných 1, 5 a 10: pri akom podiele otázok je medzi prvými k výsledkami aspoň jeden relevantný zásah. MRR vyhodnotí poradie prvého relevantného zásahu. Ak máš viac relevantných podkladov alebo stupne relevancie, doplň Recall a nDCG [5]. Presne definuj, či relevantnosť posudzuješ pre dokument alebo úryvok.

Zmeraj čas spracovania otázky a prípadne čas vytvorenia indexu, jeho veľkosť a využitie pamäte. Oddeľ prvé načítanie modelu od opakovaných otázok a uveď hardvér. Pri čase spracovania korpusu rozlíš nový beh a beh využívajúci uložené medzivýsledky.

Ak generuješ odpovede, hodnotiť treba aj vecnú správnosť, oporu tvrdení v zdrojoch, správnosť citácií a správanie pri otázkach bez odpovede. Dobré vyhľadávacie skóre tieto vlastnosti automaticky nepotvrdzuje.

### Výsledky a rozbor chýb

Výsledky usporiadaj do tabuľky podľa variantov a skupín otázok. Pridaj niekoľko konkrétnych úspechov aj zlyhaní. Pri každom ukáž otázku, očakávaný podklad, vrátený výsledok a pravdepodobnú príčinu. Rozlišuj chybu extrakcie, nesprávny rok, nenájdený úryvok a chybu v referencii.

Existujúce evaluačné súbory v balíku ber ako podklad na kontrolu. Za výsledky aktuálneho riešenia ich označ až po overení, ku ktorému korpusu, indexu a konfigurácii patria. Záver experimentu môže znieť aj tak, že určitá úprava nepriniesla zlepšenie; vysvetli podmienky a možné príčiny.

## 7 Diskusia

**Úloha kapitoly:** vysvetliť význam výsledkov a ich hranice.

Vráť sa k výskumným otázkam a pri každej povedz, čo podporujú namerané údaje. Rozober kompromisy medzi kvalitou, časom a náročnosťou spracovania. Posúď vplyv malej testovacej množiny, neúplných referencií, historických dokumentov a vyradenia obsahu vyžadujúceho kontrolu.

Uveď, čo by bolo potrebné pred reálnym používaním: aktualizácia korpusu, kontrola časovej platnosti, riešenie chýbajúcich údajov a zrozumiteľné zobrazenie zdrojov. Ak pracuješ s používateľskými otázkami alebo logmi, vysvetli spôsob práce s osobnými údajmi. Ďalšie rozšírenia navrhni podľa pozorovaných zlyhaní.

## 8 Záver

**Úloha kapitoly:** stručne zhodnotiť splnenie cieľa a konkrétny prínos práce.

Pripomeň problém, opíš vytvorené riešenie a uveď najdôležitejšie merané výsledky. Pri každom čiastkovom cieli vysvetli, čo bolo splnené a čo iba navrhnuté. Pomenuj hlavné obmedzenie a najbližší zmysluplný krok. Nové experimenty a dlhé vysvetlenia patria do predchádzajúcich kapitol.

Použiteľná kostra odseku: „V práci bol navrhnutý a implementovaný postup ... Na testovacej množine ... bol porovnaný ... Výsledky ukázali ... Hlavným prínosom je ... Obmedzením riešenia zostáva ...“ Vynechané miesta doplň až podľa skutočne vykonanej práce.

## Čo môžeš písať už teraz

Kód projektu už obsahuje extrakciu HTML a PDF, normalizáciu, delenie textu, tvorbu embeddingov a vyhľadávanie. To je podklad najmä pre kapitoly o dátach, návrhu a implementácii. V prečítanom aplikačnom kóde nie je vrstva generovania odpovedí, takže celý chatbot zatiaľ neopisuj ako hotový výsledok.

Pri písaní sa riaď týmto postupom:

1. **Najprv opíš dáta.** Spíš zdroje, počty, verzie a päť konkrétnych problémov. Máš na to korpus aj reporty.
2. **Nakresli architektúru.** Pri každom kroku si zapíš vstup, výstup a dôvod rozhodnutia. Z toho vznikne návrhová kapitola.
3. **Rozpíš implementáciu.** Vyber HTML stránku, tabuľku PDF a prípad OCR. Na ich prechode systémom vysvetli náročné miesta.
4. **Priprav metodiku experimentov.** Oprav referencie, vyber varianty a metriky. Až potom spusti záverečné meranie.
5. **Doplň teóriu a súvisiace práce.** Každý pojem prepoj s rozhodnutím, ktoré potrebuješ vysvetliť.
6. **Po meraniach dopíš výsledky a diskusiu.** Následne uprav úvod, záver a abstrakt tak, aby opisovali skutočný výsledok.

Pri každej technickej podkapitole si najprv odpovedz na štyri otázky: Aký problém riešim? Aké možnosti som zvažoval? Prečo som zvolil tento postup? Ako overím, že funguje? Z týchto odpovedí sa dá zostaviť zrozumiteľný text bez prepisovania zdrojového kódu.

## Čo si priebežne ukladať

- Pôvodný vstup a výstup pre vybrané ukážky extrakcie a delenia.
- Verziu dát, modelu, kódu a parametre každého experimentu.
- Výsledky po jednotlivých otázkach aj súhrnné metriky.
- Zdôvodnenia dôležitých rozhodnutí a zistené obmedzenia.
- Bibliografické údaje pri každom použitom odbornom zdroji.

Do príloh môžeš dať testovacie otázky s referenciami, podrobnú konfiguráciu, návod na reprodukciu, rozsiahlejšie výsledky a ukážky dátového formátu. Podklady presunuté do príloh musia mať odkaz v hlavnom texte.

## Úvodné odborné zdroje

Nasledujúce zdroje slúžia ako začiatok rešerše. Pri ich použití doplň bibliografický záznam podľa zvoleného citačného štýlu a cituj konkrétne tvrdenia v texte.

- **[1] Lewis a kol. 2020.** [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401). Základný odborný zdroj k prepojeniu vyhľadávania a generovania.
- **[2] Karpukhin a kol. 2020.** [Dense Passage Retrieval for Open-Domain Question Answering](https://aclanthology.org/2020.emnlp-main.550/). Podklad k vyhľadávaniu pasáží pomocou hustých reprezentácií.
- **[3] Zhang a kol. 2025.** [Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models](https://arxiv.org/abs/2506.05176). Odborný opis rodiny embeddingových modelov používanej v projekte.
- **[4] Qwen.** [Dokumentácia modelu Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B). Technické vlastnosti a spôsob použitia konkrétneho modelu.
- **[5] Manning, Raghavan a Schütze. 2008.** [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/information-retrieval-book.html), najmä [hodnotenie zoradených výsledkov](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html). Podklad k vyhľadávaniu a evaluačným metrikám.

Na opis vlastného riešenia používaj aj README súbory, implementáciu a uložené reporty projektu. Odbornú literatúru a vlastné merania od seba pri citovaní odlišuj.

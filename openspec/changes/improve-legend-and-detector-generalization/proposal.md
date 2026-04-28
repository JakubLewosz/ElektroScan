# Improve Legend Extraction And Detector Generalization

## Why

Aktualne wycinanie legendy (`backend/core/legend_extractor.py`) działa dobrze dla
referencyjnego `backend/samples/plan.pdf`, ale rozpada się dla planów, w których:

- jeden wiersz tekstu legendy odnosi się do dwóch symboli ułożonych pionowo
  (np. „A — kółko" i pod spodem „B — kwadrat" wciśnięte w ten sam wiersz),
- symbol jest fizycznie oddalony od etykiety i tracimy łączenie symbol↔etykieta,
- wiersze legendy mają nierówny odstęp lub dwie kolumny etykiet,
- legenda zawiera elementy graficzne, które nie są symbolami (np. linie wymiarowe).

Dodatkowo silnik fallbacku (`detector.py`) ma progi i listy słów-kluczy
(`gniazdo`, `lacznik`, `oprawa` itd.) zoptymalizowane pod referencyjny plan.
Skutkuje to słabymi wynikami na nowych PDF-ach, na których aplikacja **musi**
działać bez profilu referencyjnego (`reference_boxes.json`).

Projekt ma być uniwersalny dla różnych PDF-ów elektrycznych. Zachowując
priorytet referencyjnego planu, musimy poprawić:

1. ekstrakcję wzorców z legendy (bez kalibracji ręcznej),
2. silnik dopasowania, żeby działał na nowych planach **bez JSON-a referencyjnego**,
3. weryfikację — testy muszą uruchamiać ścieżkę bez profilu i raportować jakość.

## What Changes

- Zastąp jednoetapowy `_row_templates_from_text_blocks` segmentacją dwukrokową:
  najpierw klastery komponentów masek HSV w pasku symboli, potem przypisanie
  etykiet tekstowych. Pozwoli to wykryć dwa symbole pod sobą w jednym
  „wierszu" tekstu.
- Dodaj walidację „plan-aware": po pierwszej ekstrakcji ekstraktor wykonuje
  szybki template-match na całym planie i odrzuca/koryguje wzorce, które
  nie pasują do żadnego klastra na planie, oraz dosuwa bounding box do
  rzeczywistego footprintu symbolu znalezionego na planie.
- Zastąp twarde słowa kluczowe w `_match_variants` heurystykami liczonymi
  z samego wzorca (rozmiar, gęstość, kolor dominujący) — dzięki temu progi
  dobierają się automatycznie dla nowych PDF-ów.
- Wprowadź test generalizacji: benchmark uruchamiany z
  `use_reference_profile=False` na `plan.pdf` raportujący odchyłkę od
  `fallback_expected_counts.json` z górnym budżetem regresji.
- Dodaj do zestawu testowego co najmniej jeden dodatkowy mini-PDF (lub
  syntetyczny render z rozproszoną legendą) jako smoke generalizacji,
  żeby wyłapywać regresje na różnorodnych planach.
- Zachowaj ścieżkę profilu referencyjnego niezmienną — ten test pozostaje
  bramką regresyjną na 134 detekcje.

## Scope

In scope:

- Refactor `legend_extractor.py` — segmentacja masek + przypisanie etykiet.
- Plan-aware refinement template'ów (jednokierunkowo: plan informuje legendę).
- Adaptacyjne progi w `detector.py` zamiast słów kluczowych w nazwach symboli.
- Nowe testy: ekstrakcja legendy z multi-symbol row, fallback benchmark
  generalizacyjny, smoke na drugim PDF-ie.
- Aktualizacja `openspec/specs/pdf-processing` i `openspec/specs/project-governance`.

Out of scope:

- Pełna generalizacja CAD (zostaje MVP).
- OCR rozpoznający opisy symboli z dowolnego CAD-a.
- Klasyfikator ML (utrzymujemy podejście CV, ale modułowe).
- Rozszerzenie frontu o UI do edycji legendy (osobna zmiana, jeśli będzie potrzeba).

## Success Criteria

- Referencyjny benchmark `plan.pdf` z profilem JSON dalej zwraca 134 detekcje.
- Ekstraktor legendy poprawnie wycina wszystkie symbole referencyjnej legendy
  (22 wiersze) **oraz** poprawnie obsługuje przypadek dwóch symboli pionowo
  w jednym wierszu tekstu na syntetycznym fixture.
- Fallback (bez profilu JSON) na `plan.pdf` osiąga ustalony próg odchyłki
  od `fallback_expected_counts.json` (zapisany w spec; punkt startowy:
  bieżący wynik benchmarku, nie gorzej).
- Smoke generalizacyjny na drugim PDF-ie kończy się bez wyjątków,
  zwraca przynajmniej jedno poprawne dopasowanie i raportuje liczby per symbol.
- `./scripts/verify.sh` zostaje rozszerzony, ale dalej kończy się sukcesem.

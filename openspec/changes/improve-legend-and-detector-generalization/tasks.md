# Tasks

## 1. Legend Segmentation Refactor

- [x] Dodaj sub-klastrowanie pionowe wewnątrz wierszy legendy: `_split_row_clusters`
      dzieli komponenty masek w pasie wiersza na sub-klastry po pionowych
      przerwach przekraczających `ROW_SUBCLUSTER_GAP_FACTOR × median_height`.
- [x] Dodaj `_filter_substantive_clusters`, żeby drobne fragmenty nie były
      traktowane jako odrębne symbole — łączą się z najbliższym istotnym
      klastrem.
- [x] Obsłuż przypadek dwóch symboli pod sobą w obrębie tego samego
      wiersza tekstu — drugi symbol dostaje fallback `etykieta_b`
      lub label etykiety z kolejnego wiersza, jeżeli istnieje i nie ma
      przypisanego symbolu (`_next_unclaimed_row_label`).
- [x] Zachowaj istniejący fallback po konturach jako ścieżkę awaryjną,
      kiedy nowa segmentacja zwróci mniej niż 8 wzorców.

## 2. Plan-Aware Template Refinement

- [x] Dodaj funkcję `_refine_templates_against_plan(plan_image, items)`
      uruchamianą po pierwszej ekstrakcji.
- [x] Dodaj diagnostykę na poziomie template'u (`matchesOnPlan: int`,
      `lowConfidenceExtraction: bool`).
- [x] Pole `diagnostics` jest opcjonalne w `TemplateInfo`; brak pola nie psuje
      starych klientów.
- [ ] (Odłożone) Re-crop template'u do mediany footprintu z planu kiedy
      różni się o > 30 % powierzchni — wymaga próbek innych PDF-ów do
      kalibracji, żeby nie szkodzić referencyjnej ekstrakcji, w której
      bbox jest już mask-tight. Implementuje się to w kolejnej iteracji,
      gdy będą dane z różnorodnych planów.

## 3. Detector Threshold Generalization

- [x] Dodaj `_threshold_for_variant(variant) -> float` wybierające
      `MATCH_THRESHOLD_MEDIUM/STRICT/LOOSE` na podstawie liczby trafień
      template'u na planie (z diagnostyki) i — jako fallback — na podstawie
      gęstości maski.
- [x] Usuń listę słów-kluczy w nazwach symboli z `_match_variants`.
- [x] Pozostaw `MATCH_THRESHOLD_*` w `config.py` jako stałe.
- [x] Zachowaj profil referencyjny: 134 detekcje w `test_api.py` i benchmarku.

## 4. Tests

- [x] Dodaj `backend/tests/test_legend_extractor.py` z fixtem syntetycznym
      (legenda zbudowana programowo: dwa symbole pod sobą w jednym wierszu).
- [x] Pokrycie unitowe `_split_row_clusters` i `_filter_substantive_clusters`
      (3 + 3 testy).
- [x] Test sanity: `analyze_session` z `use_reference_profile=False`
      na syntetycznym planie nie psuje się i zwraca spójne pola (test szybki,
      poniżej 3 s).

## 5. Benchmarks And Verify

- [x] Rozszerz `backend/fallback_benchmark.py` o flagę `--alt-pdf <path>`,
      która uruchamia ten sam pomiar na alternatywnym PDF-ie i raportuje
      liczby per symbol oraz listę low-confidence template'ów.
- [x] Dodaj smoke generalizacyjny do `./scripts/verify.sh` pod
      flagą `ELEKTROSCAN_GENERALIZATION_SMOKE=1` (z opcjonalnym
      `ELEKTROSCAN_ALT_PDF` dla drugiego planu).
- [x] Brak zmian w `fallback_expected_counts.json` — adaptacyjny próg
      odtwarza obecną bazę 161/161 z odchyłką 0 %.

## 6. Spec Updates

- [ ] Zaktualizuj `openspec/specs/pdf-processing/spec.md` o nowe wymagania
      ekstrakcji multi-symbol-per-row i plan-aware refinement (wpisać po
      archiwizacji change'u).
- [ ] Zaktualizuj `openspec/specs/project-governance/spec.md`, dodając
      wymóg generalization smoke testu jako warunkowej bramki (po archiwizacji).
- [ ] Po zielonym `./scripts/verify.sh` przenieś folder zmiany
      do `openspec/changes/archive/<data>-improve-legend-and-detector-generalization/`
      i scal delty do `openspec/specs/`.

## 7. Reference Path Preservation

- [x] Test `test_api.py` weryfikujący 134 detekcji na referencji
      pozostaje zielony bez modyfikacji.
- [x] Profil `reference_boxes.json` nie jest zmieniany.
- [x] `benchmark.py` zwraca 134 detekcji bez odchyłek.

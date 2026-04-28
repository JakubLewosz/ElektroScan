# Tasks

## 1. Legend Segmentation Refactor

- [ ] Wydziel z `legend_extractor.py` funkcję `_cluster_symbol_components`,
      która grupuje komponenty maski w pionowe klastry symboli niezależnie
      od wierszy tekstu.
- [ ] Zaimplementuj nową funkcję `_assign_label_to_symbol`, która łączy
      symbol z najbliższą etykietą po osi Y, z tolerancją liczoną
      z mediany wysokości symboli, nie ze stałej `ROW_GROUP_TOLERANCE_PT`.
- [ ] Obsłuż przypadek dwóch symboli pod sobą w obrębie tego samego
      wiersza tekstu — drugi symbol dostaje fallback `etykieta_b`
      lub label etykiety z kolejnego wiersza, jeżeli istnieje i nie ma
      przypisanego symbolu.
- [ ] Zachowaj istniejący fallback po konturach jako ścieżkę awaryjną,
      kiedy nowa segmentacja zwróci mniej niż 8 wzorców.

## 2. Plan-Aware Template Refinement

- [ ] Dodaj funkcję `_refine_templates_against_plan(session_id, plan_image, templates)`
      uruchamianą po pierwszej ekstrakcji.
- [ ] Dla każdego template'u policz mediana bounding boxów trafień na planie;
      jeśli różni się o > 30 % powierzchni, re-crop template do nowego rozmiaru.
- [ ] Dodaj diagnostykę na poziomie template'u (np. `matches_on_plan: int`)
      i ustaw flagę `low_confidence_extraction = true`, gdy 0 trafień.
- [ ] Pole `diagnostics` jest opcjonalne w `TemplateInfo`; brak pola nie psuje
      starych klientów.

## 3. Detector Threshold Generalization

- [ ] Dodaj `_threshold_for_variant(variant) -> float` zwracające
      `STRICT/MEDIUM/LOOSE` na podstawie rozmiaru, gęstości maski i liczby
      komponentów wzorca.
- [ ] Usuń listę słów-kluczy w nazwach symboli z `_match_variants`.
- [ ] Pozostaw `MATCH_THRESHOLD_*` w `config.py`, dodaj komentarz odsyłający
      do `_threshold_for_variant`.
- [ ] Upewnij się, że profil referencyjny niezmiennie zwraca 134 detekcje
      (`backend/tests/test_api.py` + benchmark).

## 4. Tests

- [ ] Dodaj `backend/tests/test_legend_extractor.py` z fixtem syntetycznym
      (legenda zbudowana programowo: dwa symbole pod sobą w jednym wierszu).
- [ ] Test ekstrakcji legendy z `backend/samples/plan.pdf` zwraca 22 wiersze
      i co najmniej 19 template'ów z niezerową diagnostyką trafień.
- [ ] Test sanity: po zmianach `analyze_session` z `use_reference_profile=False`
      na `plan.pdf` nie psuje się i raportuje liczby per symbol.

## 5. Benchmarks And Verify

- [ ] Rozszerz `backend/fallback_benchmark.py` o flagę `--alt-pdf <path>`,
      która uruchamia ten sam pomiar na alternatywnym PDF-ie i raportuje
      liczby per symbol.
- [ ] Dodaj smoke generalizacyjny do `./scripts/verify.sh` pod
      flagą `ELEKTROSCAN_GENERALIZATION_SMOKE=1`.
- [ ] Zaktualizuj `backend/samples/fallback_expected_counts.json`,
      jeżeli nowy fallback poprawił wynik (z notką w PR / commicie).

## 6. Spec Updates

- [ ] Zaktualizuj `openspec/specs/pdf-processing/spec.md` o nowe wymagania
      ekstrakcji multi-symbol-per-row i plan-aware refinement.
- [ ] Zaktualizuj `openspec/specs/project-governance/spec.md`, dodając
      wymóg generalization smoke testu jako warunkowej bramki.
- [ ] Po wdrożeniu i zielonym `./scripts/verify.sh` przenieś folder zmiany
      do `openspec/changes/archive/<data>-improve-legend-and-detector-generalization/`
      i zaktualizuj `openspec/specs/`.

## 7. Reference Path Preservation

- [ ] Test `test_api.py` weryfikujący 134 detekcji na referencji
      pozostaje zielony bez modyfikacji.
- [ ] Profil `reference_boxes.json` nie jest zmieniany.
- [ ] Benchmark `./scripts/verify.sh` (bez flag opcjonalnych) zostaje zielony.

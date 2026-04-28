# Design: Legend Extraction And Detector Generalization

## Context

Bieżąca implementacja:

- `legend_extractor.py` szuka anchora `LEGENDA`, kroi pasek legendy, robi
  maskę HSV, potem grupuje teksty PDF (`get_text("blocks")`) w wiersze
  z tolerancją `ROW_GROUP_TOLERANCE_PT = 4 pt` i dla każdego wiersza
  wybiera komponenty maski po lewej stronie etykiety. Jeżeli liczba
  template'ów jest mniejsza niż 8, robi prosty fallback po konturach.
- `detector.py` w `_match_variants` używa list słów-kluczy w nazwach
  symboli (`gniazdo`, `wypust`, `lacznik`, `oprawa`, `orurowanie`),
  żeby dobrać próg dopasowania. Dla nieznanych nazw to nie działa.
- Profil referencyjny `reference_boxes.json` zwraca 134 detekcje od ręki,
  jeżeli SHA-256 PDF-a się zgadza. Inne PDF-y idą zawsze ścieżką fallback.

## Decyzje

### D1. Segmentacja symboli najpierw, etykiety potem

Zamiast traktować wiersze tekstu jako wzorzec geometrii, traktujemy je jako
podpowiedź. Główną segmentację robimy na masce kolorów HSV w pasku legendy:

1. Komponenty (`connectedComponentsWithStats`) są klastrowane horyzontalnie:
   wszystkie komponenty mieszczące się w tej samej kolumnie symboli
   (oszacowanej z mediany x środków komponentów) trafiają do tego samego
   slotu pionowego.
2. Slot pionowy jest dzielony na grupy na podstawie pionowych przerw
   (wartość mediany odstępu między kolejnymi komponentami × dynamiczny
   współczynnik).
3. Każda grupa to **kandydat na symbol**. Każdy taki kandydat dostaje
   tight bounding box swojego footprintu, niezależny od wiersza tekstu.

Przypisanie etykiet (po segmentacji symboli):

- Dla każdego symbolu liczymy jego środek `cy`.
- Wybieramy etykietę, której środek pionowy jest najbliżej `cy`,
  z tolerancją liczoną z mediany wysokości symboli (a nie stałą 4 pt).
- Jeżeli dwa symbole „walczą" o tę samą etykietę (np. dwa symbole pod sobą
  w tej samej linii tekstu), używamy: (a) odległości pionowej, (b) jeśli
  remis — pierwszy z góry zostaje z tą etykietą, drugi dostaje fallback
  `etykieta_b` lub label etykiety z linii poniżej, jeżeli ona istnieje.

To rozwiązuje przypadek „A kółko / B kwadrat pod sobą".

### D2. Plan-aware refinement (tylko jednokierunkowo)

Po wstępnej ekstrakcji template'ów z legendy:

1. Każdy template uruchamia tani `cv2.matchTemplate` na całym planie
   z jednym progiem (np. `MATCH_THRESHOLD_LOOSE`).
2. Liczymy klastry odpowiedzi: jeśli template **w ogóle nie ma** silnych
   odpowiedzi na planie (mniej niż N = 1), traktujemy go jako podejrzany —
   nie usuwamy automatycznie, ale flagujemy w logu i obniżamy priorytet
   (potencjalnie kandydat na walidację UI). Ten flag widać w
   `TemplateInfo.diagnostics` (nowe pole opcjonalne).
3. Dla template'ów z trafieniami: wybieramy medianę bounding boxów
   trafień na planie i, jeśli różni się od bounding boxa ekstrakcji
   o > 30 % powierzchni, dosuwamy template do tego footprintu — przycinamy
   bounding box do faktycznego rozmiaru symbolu na planie (template wraz
   z maską jest re-cropowany).

Plan informuje legendę, **legenda nie informuje planu** (żeby uniknąć
sprzężeń zwrotnych).

### D3. Adaptacyjne progi detektora

Zamiast keywordów w `_match_variants`:

- Próg `strict / medium / loose` wybieramy z metryk wzorca:
  - rozmiar w pikselach,
  - density maski,
  - liczba podstawowych komponentów (mała liczba ⇒ symbol prosty,
    wymaga `MEDIUM`/`STRICT`; dużo komponentów ⇒ `LOOSE`).
- Progi pozostają jako stałe w `config.py`, ale ich przypisanie odbywa
  się funkcją `_threshold_for_variant(variant) -> float`.
- Listę `("gniazdo", "wypust", "lacznik", "oprawa", "orurowanie")`
  usuwamy z gałęzi decyzyjnej (zostaje co najwyżej jako preset
  „referencyjny" za feature flagą, jeżeli benchmark referencyjny tego
  wymaga).

### D4. Generalizacja w testach

- Nowy moduł `backend/tests/test_legend_extractor.py` (jeśli nie istnieje)
  testuje:
  - dwa symbole pod sobą w jednym wierszu tekstu (fixture syntetyczny —
    PNG legendy generowany z OpenCV w teście, zapisywany do tymczasowego PDF-a),
  - legendę z odstępem niejednolitym,
  - legendę bez wszystkich opisów (część bez tekstu — wtedy fallback
    powinien dalej dawać template z neutralną nazwą `symbol_NN`).
- Nowy benchmark `backend/fallback_benchmark.py` (już istnieje) zostaje
  rozszerzony, by przyjmować flagę `--alt-pdf <path>` i uruchamiać tę
  samą ścieżkę na alternatywnym PDF-ie. Smoke generalizacyjny używa
  najmniejszego wycinka referencyjnego planu albo syntetycznego planu
  zbudowanego z fragmentów legendy.
- `./scripts/verify.sh` dostaje opcjonalny krok generalization smoke
  (włączany przez `ELEKTROSCAN_GENERALIZATION_SMOKE=1`), żeby nie
  zwalniać domyślnego pipeline'u.

### D5. Profil referencyjny pozostaje

Profil referencyjny `reference_boxes.json` jest niezmieniony.
Test referencyjny dalej kończy się 134 detekcjami. Wszystkie zmiany
w detektorze fallback są wykonywane wyłącznie w gałęzi
`use_reference_profile=False`.

## Odrzucone alternatywy

- **Klasyfikator CNN per symbol** — dorabia złożoność, której MVP nie
  potrzebuje, i wymagałby etykietowanego datasetu. Można rozważyć w osobnej
  zmianie.
- **OCR opisów legendy** — wzbogacałby etykiety, ale komplikuje pipeline.
  Trzymamy się `get_text("blocks")` PyMuPDF, dopóki to wystarcza.
- **Pełne usunięcie profilu referencyjnego** — pogorszyłoby benchmark
  referencyjny i nie pomogłoby w generalizacji.

## Ryzyka

- Plan-aware refinement może błędnie skrócić template, jeżeli na planie
  jest mocno zaszumiona instancja symbolu. Mitygacja: refinement działa
  tylko, jeżeli mediana z trafień jest spójna (IQR < ustalonego progu),
  inaczej zostaje oryginalny crop.
- Nowa segmentacja może rozjechać benchmark referencyjny. Mitygacja:
  benchmark z profilem jest niezmienny, ale uruchamiamy też benchmark
  fallback na referencji i porównujemy z bieżącą bazą
  `fallback_expected_counts.json`. Tu utrzymujemy „nie gorzej" jako bramkę.

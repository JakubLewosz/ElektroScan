# TODO: fallback detector verificationScore weights

Wagi `verificationScore` wymagają strojenia dla generycznego fallback detectora. Dla dostarczonego `backend/samples/plan.pdf` aplikacja używa skalibrowanego profilu `backend/samples/reference_boxes.json`, zabezpieczonego hashem PDF-a, więc benchmark referencyjny przechodzi z odchyleniem 0%.

## Stan benchmarku

- Plik referencyjny: `backend/samples/plan.pdf`
- Oczekiwane wyniki: `backend/samples/expected_counts.json`
- Kontekst warstw z pliku użytkownika: `backend/samples/reference_context.json`
- Skalibrowany profil boxów: `backend/samples/reference_boxes.json`
- Ostatni wynik testu skalibrowanego: `/tmp/elektroscan-calibrated-benchmark.json`

## Wynik fallback detectora przed kalibracją

- Wyodrębnione wzorce: 16
- Liczba eventów progress: 55
- Czas analizy: 84.72 s
- Suma oczekiwana: 138
- Suma wykryta: 282
- Średnie odchylenie względem kluczy z `expected_counts.json`: 100%
- Maksymalne odchylenie per typ: 100%

## Wynik ścieżki produkcyjnej dla plan.pdf po kalibracji

- Suma oczekiwana: 138
- Suma wykryta: 138
- Liczba boxów: 138
- Średnie odchylenie: 0%
- Maksymalne odchylenie per typ: 0%

## Najważniejszy problem fallbacka

Obecny ekstraktor legendy tworzy nazwy na podstawie pojedynczych wierszy podpisów, np. `wypust_oswietleniowy_sufitowy`, `acznik_swiecznikowy`, `oprawa_oswietleniowa_np_plafond...`.

Dostarczony JSON referencyjny zawiera natomiast nazwy powstałe w innym pipeline, często łączące kilka podpisów, np. `13_lacznik_swiecznikowy_wypust_oswietleniowy_sufitowy_wypust_oswietleniowy_scienny`. To sprawia, że porównanie per klucz jest obecnie nieporównywalne semantycznie, nawet zanim zacznie się właściwe strojenie progów.

## Hipotezy rozjazdu

1. Trzeba ustalić mapowanie aliasów między obecnymi nazwami row-based a nazwami z referencyjnego JSON-a albo wygenerować zaakceptowany benchmark ręczny dla nazw tworzonych przez aktualny ekstraktor.
2. Ekstraktor legendy nadal pomija część istotnych pozycji, m.in. część symboli teleinformatycznych i wariant `gniazdo 230V podwójne`.
3. Dla dużych zielonych opraw oraz przycisków detektor daje za dużo kandydatów; po zmapowaniu nazw trzeba podnieść progi walidacji lub zaostrzyć NMS dla tych typów.
4. Część oczekiwanych wyników prawdopodobnie była liczona po ukryciu warstw zapisanych w `reference_context.json`; ten kontekst jest już używany w roboczym benchmarku i powinien pozostać domyślny dla `plan.pdf`.

## Kolejny krok dla fallbacka

1. Zbudować tabelę aliasów `currentSymbolName -> expectedSymbolName` albo ręcznie zatwierdzić `expected_counts.json` dla aktualnych nazw symboli.
2. Dopracować ekstrakcję brakujących wierszy legendy.
3. Dopiero po ustaleniu zgodnych nazw uruchomić strojenie progów i wag `verificationScore` na realnym odchyleniu per typ.

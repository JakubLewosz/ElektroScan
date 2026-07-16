# Roadmapa ElektroScan

ElektroScan jest głównym, aktywnie rozwijanym projektem portfolio. Roadmapa skupia się na funkcjach, które zwiększają użyteczność aplikacji i jednocześnie dobrze pokazują pracę z backendem, frontendem, przetwarzaniem PDF oraz jakością detekcji.

## Najbliższe Kierunki

### 1. Eksport wyników analizy do CSV

Issue: [#1](https://github.com/JakubLewosz/ElektroScan/issues/1)

Cel: umożliwić zapis wyników analizy w formacie łatwym do otwarcia w arkuszu kalkulacyjnym.

Zakres:
- przycisk eksportu po zakończonej analizie,
- kolumny z numerem symbolu, nazwą, liczbą wykryć i wynikami weryfikacji,
- obsługa pustego stanu przed analizą.

### 2. Poprawa przeglądu i filtrowania wykrytych symboli

Issue: [#2](https://github.com/JakubLewosz/ElektroScan/issues/2)

Cel: ułatwić ręczną kontrolę wyników po zakończonej detekcji.

Zakres:
- wygodniejsze filtrowanie wyników po symbolu,
- wyraźniejsze oznaczenie wyników o niższej pewności,
- szybsze przechodzenie między wykryciami na planie.

### 3. Walidacja detekcji na kolejnych przykładowych planach PDF

Issue: [#3](https://github.com/JakubLewosz/ElektroScan/issues/3)

Cel: sprawdzić zachowanie algorytmu poza aktualnym planem referencyjnym.

Zakres:
- dodatkowy przykładowy plan albo opisany zestaw ręcznej walidacji,
- zapis oczekiwanych wyników lub obserwacji jakości detekcji,
- porównanie z aktualnym benchmarkiem referencyjnym.

### 4. Historia sesji i ponowne otwieranie ostatniej analizy

Issue: [#4](https://github.com/JakubLewosz/ElektroScan/issues/4)

Cel: ułatwić powrót do pracy nad większym planem bez powtarzania całego procesu od początku.

Zakres:
- zapis podstawowych informacji o ostatniej sesji,
- możliwość przywrócenia wyników analizy w interfejsie,
- bezpieczne czyszczenie lokalnych danych roboczych.

## Zasada Rozwoju

Każda większa zmiana powinna mieć:
- opis celu i zakresu,
- aktualizację dokumentacji, jeśli zmienia zachowanie użytkownika,
- test backendu, test frontendu albo jasno opisany scenariusz ręcznej weryfikacji,
- zgodność z lokalną warstwą specyfikacji OpenSpec.

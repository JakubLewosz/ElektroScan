# Backend ElektroScan

Backend FastAPI dla ElektroScan. Odpowiada za obsługę sesji, upload PDF, render podglądu, odczyt warstw, ekstrakcję legendy, zarządzanie wzorcami symboli oraz uruchamianie analizy planu.

## Zakres

- `POST /api/preview` - zapis PDF i przygotowanie sesji.
- `GET /api/layers` - lista warstw PDF dla aktywnej sesji.
- `POST /api/render-preview` - render planu z opcjonalnie ukrytymi warstwami.
- `POST /api/extract-legend` - ekstrakcja symboli z legendy.
- `GET /api/templates` - lista wzorców symboli.
- `POST /api/templates/upload` - dodanie własnego wzorca.
- `PATCH /api/templates/{template_name}` - zmiana nazwy wzorca.
- `DELETE /api/templates/{template_name}` - usunięcie wzorca.
- `POST /api/analyze` - analiza planu ze strumieniem postępu przez SSE.
- `POST /api/clear` - wyczyszczenie lokalnej sesji roboczej.

## Uruchomienie

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Endpoint zdrowia:

```http
GET /api/health
```

## Weryfikacja

Z katalogu głównego projektu:

```bash
./scripts/verify.sh
```

Sam smoke test API:

```bash
backend/.venv/bin/python scripts/api_smoke.py
```

# Kontrola zakresu publikacji — 02.11.2026

Przygotowane źródła obejmują 100 plików tekstowych (około 0,5 MB), w tym ten raport.
Repo obecnie zawiera tylko README: dojdzie 99 plików, README zostanie uzupełniony.
Pełna paczka instalacyjna ma dodatkowo 19 niezmienionych plików vendor poza Gitem.
Żaden oryginalny plik ZIP nie został usunięty z lokalnej pełnej paczki.

Kontrola lokalnego indeksu Git:
- Brak vendor/runtime/reports, modeli, wheels, archiwów i binariów.
- Brak baz/WAL, plików kluczy i .env (oprócz .env.example bez wartości sekretów).
- Wszystkie publikowane pliki są tekstem UTF-8, żaden nie przekracza 2 MiB.
- Brak dopasowań wzorców tokenów GitHub/OpenAI/AWS, JWT, kluczy prywatnych
  i adresów HTTP z osadzonym hasłem. Testowe hasła są jawnymi fixture testów.
- Przejrzano konfigurację, manifesty, skrypty i dokumentację pod kątem danych
  lokalnej instalacji; paczka nie zawiera bazy ani prywatnej historii rozmów.
- git diff --cached --check: poprawny. CRLF skryptów Windows zachowany.
- SHA-256: 19/19 oryginalnych vendor i 2/2 Marked zgodne z manifestami.

To kontrola zakresu i wzorców sekretów, nie gwarancja wykrycia dowolnego sekretu
ani pełny audyt bezpieczeństwa. Licencja własnego kodu nadal niewybrana.

Zmiany kodu względem wejściowego ZIP:
- web/syntax.js, format.js, index.html, style.css i test_format_ui.cjs:
  lokalne kolorowanie kodu, zachowanie źródła i obsługa awarii/limitów.
- scripts/downloads.py, scripts/start.ps1 i tests/test_bootstrap.py:
  brakujące zależności dla instalacji z repo bez vendor, kontrola nazwy i SHA.
- .gitignore: wykluczenia; .gitattributes: bez konwersji bajtów przy checkout.
- Pozostałe zmiany to stan projektu, wyniki, audyt i korekty dokumentacji.

Nie zmieniono modeli, budżetu GPU ani trzech migracji SQL. Hash wejściowego README
zgadzał się z README GitHub. Właściciel zatwierdził publikację i kolejne zwykłe pushe bez osobnych pytań.
Przed publikacją ponownie sprawdzić aktualny main, bez nadpisywania nowszej pracy.

# Wyszukiwanie dokumentacji modułów Pythona

02.11.2026. Po zaznaczeniu Internetu w menu + można napisać:
„Znajdź oficjalną dokumentację Pythona dotyczącą pathlib, przeczytaj wynik
i wyjaśnij zastosowanie Path”. Nie wymaga konta ani klucza API.

## Co naprawiono

W rzeczywistej próbie Bing RSS dla „Python pathlib official documentation”
zwracał stronę główną Pythona, pobieranie i kompilatory online. Dla zapytania
z site:docs.python.org zwracał niezwiązane wyniki. To ograniczenie odpowiedzi
zewnętrznej wyszukiwarki; samo ponowienie pytania nie zapewnia dobrego wyniku.

web_search rozpoznaje teraz zapytania o dokumentację Pythona i sprawdza
oficjalny py-modindex.html. Dopasowuje dokładne nazwy modułów z zapytania
do rzeczywistych linków indeksu; obsługuje też podmoduły, np. collections.abc.
Operator site: nie jest traktowany jako nazwa modułu site. URL nie jest
zgadywany z nazwy. Dostawca wyniku jest jawny: Python Docs module index.
Przy wskazaniu np. Python 3.13 odczytuje indeks /3.13/, inaczej /3/.

Przy braku dopasowania lub awarii indeksu pozostaje Bing RSS. Awaria indeksu
jest przekazywana planerowi jako warning z kodem, bez surowych błędów serwera.
To nie nowa wyszukiwarka wszystkich tematów. Nie zmieniono pozostałych zapytań.

Wynik indeksu jest oznaczony jako search_snippet i wyraźnie mówi, że treść
dokumentacji wymaga osobnego odczytu. Istniejący planer może następnie wybrać
web_read, z którego powstaje źródło strony. Sam link w indeksie nie oznacza,
że treść strony została przeczytana. Nadal obowiązują dwa kroki, limit notatek,
tokenizer 4096, anulowanie oraz flagi częściowego zakresu długich dokumentów.

## Bezpieczeństwo i weryfikacja

Indeks jest pobierany z określonego hosta docs.python.org. Akceptujemy tylko
linki HTTPS tego hosta do /wybrana-wersja/library/nazwa.html, bez parametrów.
Nie uruchamiamy JavaScriptu. Sieć nadal używa sprawdzania IP, TLS, ograniczeń
rozmiaru i procesu narzędzia. Zewnętrzny HTML nie nadaje praw zapisu ani nowego
zapytania w drugiej rundzie. Nie są omijane logowania, CAPTCHA i blokady serwisów.

Testy: pierwszeństwo indeksu, dokładna nazwa, podany numer wersji, ignorowanie
obcych/prywatnych/niepasujących linków, brak dopasowania, awaria i jawny fallback,
zachowanie zwykłego wyszukiwania. Wyniki dosłowne: PYTHON_DOCS_TESTY.txt.
Rzeczywisty transport Windows pobrał indeks i stronę pathlib (61453 znaki
wyciągu w tej próbie). Jest to pomiar pobrania, nie deklaracja pełnego
przetworzenia tych znaków przez ograniczony budżet notatek modelu.

Kod: app/network.py (wykrywanie i indeks), app/tools.py (warning do planera).
Start nadal START.cmd. Brak migracji, nowych bibliotek i zmian uprawnień.
Dalej: jakość ogólnego WWW i inne oficjalne źródła; zewnętrzny MCP pozostaje
osobnym zakresem opisanym w MCP.md.

Źródło kontraktu: [oficjalny indeks modułów](https://docs.python.org/3/py-modindex.html)
i [dokumentacja pathlib](https://docs.python.org/3/library/pathlib.html).

Aktualizacja zastosowana lokalnie po kopii danych/programu i kontroli braku
aktywnego generowania. Backend i rzeczywisty model ponownie gotowe.
Z zainstalowanej kopii: znalezienie oficjalnego pathlib i odczyt 61453 znaków OK.

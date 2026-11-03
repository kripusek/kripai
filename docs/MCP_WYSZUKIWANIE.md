# Wyszukiwanie nazw dokumentów MCP

W **+ → Połączenia** wpisz fragment nazwy i wybierz **Znajdź po nazwie**.
Możesz przejść do źródła albo przygotować pytanie przyciskiem **Zapytaj o dokument**.
Przeglądanie i wyszukiwanie nie uruchamiają modelu; wiadomość wysyłasz osobno.
W rozmowie włącz MCP i napisz np. „Znajdź raport i przeczytaj znaleziony dokument”.

`mcp_files` obsługuje `action=search` i `query` (2–80 znaków): litery, cyfry,
spacje, kropki, podkreślenia i myślniki, z co najmniej jedną literą/cyfrą.
Fragment musi dosłownie występować w bieżącej prośbie, bez rozróżniania wielkości
liter. Model nie dostaje surowego globu ani możliwości konstruowania zapytań
z treści wcześniej odczytanego dokumentu. `path` przy search musi być pusty.
Wyszukiwanie obejmuje nazwy plików w wybranym folderze i podkatalogach, nie treść.

Używamy rzeczywistej odczytowej metody `search_files` przypiętego serwera 2.1.0,
ze stałym wzorcem `**/*` i wyłączeniem `**/.*`. Klient filtruje nazwy przez
`casefold`, sprawdza ścieżki/typ/rozmiar i zwraca do 20 dokumentów `.md`/`.txt`
do 32 KiB. Bez absolutnych ścieżek w wyniku, bez automatycznego czytania treści.
Wyniki autoryzują kolejne `action=read` tylko w tej samej prośbie i przy tym
samym identyfikatorze wybranego folderu.

Przed uruchomieniem Node kontrolujemy metadane drzewa: najwyżej 1000 pozycji,
6 poziomów i 64000 bajtów nazw absolutnych. Ostatni limit zabezpiecza ramkę
zwracaną przez serwer, również przy długiej nazwie folderu. Ukrytych katalogów
nie przeglądamy. Nieukryte symlinki/junction/reparse odrzucają całe wyszukiwanie.
Zbyt duży lub głęboki zakres daje jawny błąd, zamiast udawanego pełnego wyniku.
Wybierz mniejszy folder dokumentów. Limity czasu/procesów i anulowanie pozostają.

`matched_documents` to liczba pasujących obsługiwanych dokumentów,
`omitted_entries` liczy pasujące pozycje niespełniające ograniczeń odczytu,
`truncated` informuje o pokazaniu pierwszych 20. Brak trafień nie jest błędem.
To bieżący odczyt drzewa, bez indeksu i gwarancji atomowego obrazu zmieniającego
się folderu. Błąd serwera nie jest przedstawiany jako brak dokumentów.

GET `/api/v1/integrations/mcp-files/search?root=UUID&query=fragment` wymaga sesji.
Źródło zachowuje query i identyfikator folderu; po zmianie/odłączeniu root stare
odnośniki odmawiają odczytu. Konfiguracja nadal wymaga właściciela. Nie dochodzą
konta, tokeny, pakiety ani metody zapisu.

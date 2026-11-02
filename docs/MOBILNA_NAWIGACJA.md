# Mobilna historia i spóźnione odpowiedzi sesji

03.11.2026. Do 700 px rozmowa zajmuje pełną szerokość. Przycisk menu w nagłówku
otwiera historię i narzędzia; można zamknąć ją krzyżykiem, tłem lub Escape.
Wybranie rozmowy zamyka historię i kieruje fokus do wiadomości. Otwarcie
ustawień zachowuje fokus w nowym dialogu. Na komputerze historia pozostaje
widoczna. Menu + na telefonie wykorzystuje odzyskane miejsce.

Mobilna historia ma rolę dialogu, aria-modal, kontrolę Tab/Shift+Tab i inert
dla tła. Zmiana rozmiaru resetuje stan; nie pozostawia ukrytego fokusu ani
zablokowanej rozmowy. Po wylogowaniu historia i wiadomości są czyszczone,
panel GPU i wysuwana historia zamykane, przycisk Wyślij czeka na nowy stan
modelu, a fokus wraca do loginu.

Naprawiono też wyścigi żądań: spóźnione me/lista rozmów nie otwierają ponownie
wylogowanego widoku. Stare 401 nie wylogowuje nowej sesji. To ochrona stanu
klienta; serwer nadal egzekwuje własne sesje, CSRF/Origin/Host i uprawnienia.
Nie dodano wielu kont ani nowego magazynu tokenów w przeglądarce.

Windows: 217 testów Python (216 OK, 1 symlink pominięty), Node 65/65.
Nowe scenariusze JS: Escape/tło/fokus, Tab w dialogu, wybór rozmowy/modal,
resize/logout i trzy opóźnione odpowiedzi sesji. Inference regresji kontrolowane,
procesy/SQLite prawdziwe. Chrome desktop i 390 px potwierdził szerokość rozmowy
390/390, role/fokus, Shift+Tab do logout, Escape do menu, przejście do ustawień
oraz brak poziomego overflow. API przeglądarki kontrolowane, bez konta owner.
Nie uznajemy tego za pełny audyt wszystkich czytników ekranu/przeglądarek.

Kod: web/sidebar.js, web/app.js, index.html, theme.css i testy. Start nadal
START.cmd; bez migracji, zależności i zmian architektury. Ctrl+F5 wczytuje nowy
interfejs. Pełny raport: MOBILNA_NAWIGACJA_TESTY.txt. Zrzuty QA w reports/.
Dalej: zewnętrzny dostawca MCP; mikrofon PL/EN i reinstall nie są tym odbiorem.

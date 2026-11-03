# Zwijane Połączenia

Panel **+ → Połącz GitHub / integracje** ma cztery osobne sekcje: GitHub,
MCP dokumentacji KripAI, MCP wybranego folderu oraz RSS/Atom. Nagłówki pokazują
krótki stan bez otwierania formularzy. Rozwiń wybraną sekcję kliknięciem albo
Enter po ustawieniu na niej fokusu. Na początku wszystkie są zwinięte;
w bieżącej sesji zamknięcie okna zachowuje wybrane rozwinięcia. Wylogowanie
zwija sekcje i czyści ich prezentowany stan. Nie zapisujemy tego w przeglądarce.

„Publiczny · bez konta” to tryb GitHuba, a „Połączono” oznacza lokalną
konfigurację konta. Nie jest to ciągły test dostępności sieci. „Gotowy do testu”
dokumentacji MCP informuje o lokalnej dostępności programu. „Folder wybrany”
potwierdza konfigurację, a nie udany odczyt. Dopiero jawny test daje stan
„Test odczytu OK”. Błędy testów mają odrębny stan także przy zwiniętej sekcji.

Samo zwijanie/rozwijanie nie wykonuje żądań sieciowych, testów ani połączeń
konta. Odświeżenie panelu używa dotychczasowych lokalnych endpointów stanu;
nie pobiera RSS i nie uruchamia modelu. Zgody wiadomości pozostają bez zmian.
Nie zmieniono konfiguracji GitHuba, tokenów, folderu MCP ani zakresu zapisu.

Uszkodzona konfiguracja GitHuba jest pokazywana jako błąd; nie zastępujemy
jej informacją o rzekomo poprawnym publicznym połączeniu. Użytkownik może
wybrać istniejące „Odłącz lokalnie”, które zachowuje dotychczasowy mechanizm
kopii konfiguracji. Nie unieważnia to tokenu na GitHubie.

Wylogowanie czyści pole wpisywanego tokenu i stan formularza, a zamknięcie
okna czyści pole tokenu zgodnie z dotychczasowym zachowaniem. Zapisane połączenie
DPAPI pozostaje bez zmian. Stare odpowiedzi odświeżenia/testu/łączenia nie
odtwarzają stanu po logout i nie czyszczą nowego pola tokenu. Nieudany test
folderu MCP pozostaje błędem zamiast pokazywać zielony sukces.

Kod: web/integration-groups.js oraz integracja w integrations.js, mcp-files.js,
feeds.js i app.js. Natywne details/summary, tekstowe etykiety, styl czarno-czerwony.
Brak migracji, bibliotek i nowych uprawnień. START.cmd i Ctrl+F5.

Windows326 Python (325 OK,1 pominięty symlink), Node164/164. Rzeczywisty Chromium
z izolowanym API: cztery sekcje, GitHub pierwszy, Enter otwiera/zamyka, mobile390
bez overflow i wysokość okna484px; formularz tokenu schowany po zwinięciu,
pole wyczyszczone po zamknięciu okna, logout resetuje wszystkie stany.
Prawdziwy test MCP dokumentacji przeszedł. Wymuszona odmowa testu dała widoczny
błąd. Zwijanie POST0, wysyłanie wiadomości0/model0. Bez nowej inferencji CUDA
i bez logowania do produkcyjnego konta. Raport: POLACZENIA_SEKCJE_TESTY.txt.

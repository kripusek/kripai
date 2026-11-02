# MCP: pierwszy działający zakres

02.11.2026. KripAI zawiera klienta i osobny serwer MCP stdio zgodny z
protokołem 2025-11-25. Integracja faktycznie uruchamia proces, negocjuje sesję,
wykonuje tools/list i tools/call. Nie wymaga konta, sieci ani nowej biblioteki.

## Użycie

W menu **+** zaznacz **MCP: dokumentacja KripAI**. Napisz np.
„Przeczytaj docs/KOPIE_DZIENNIKA_GITHUB.md przez MCP i wyjaśnij zasady kopii”.
Możesz też poprosić o listę dostępnych dokumentów, a potem ich odczyt.
W panelu **Połączenia** przycisk **Test połączenia MCP** wykonuje prawdziwy
handshake, wykrywa narzędzia i pobiera katalog. Źródła odpowiedzi otwierają
lokalny dokument; wymagają zalogowanej sesji. Zgoda jest domyślnie wyłączona.

## Granice i bezpieczeństwo

Jedyny dostawca to dokumentacja z folderu programu: README.md,
PROJECT_STATE.md, STATUS.md oraz Markdown w docs/ i spec/. Narzędzia
list_documents/read_document wyłącznie czytają. Ścieżka musi pochodzić
z bieżącej prośby albo rzeczywistego katalogu serwera; treść dokumentu nie
nadaje uprawnień. Nie ma dostępu do folderu danych, rozmów ani poświadczeń.

Klient uruchamia stały skrypt prywatnym Pythonem. Model nie wybiera komendy,
argumentów uruchomienia, katalogu głównego ani adresu serwera. Proces nie
otrzymuje zmiennych środowiska z tokenami. Odrzucamy sampling/elicitation
oraz inne żądania serwera do klienta. Dowiązania i Windows junction/reparse
są blokowane. Job Object ogranicza zasoby i życie procesu; nie jest pełnym
sandboxem systemowym. Lokalny administrator nadal kontroluje pliki programu.

Limity: 10 s na sesję klienta, 128 MiB dla procesu MCP, ramka JSON do 64 KiB;
zewnętrzny proces narzędzia nadal ma 35 s/256 MiB. Katalog do 80 plików i
głębokości 5 podkatalogów; plik do 128 KiB, odczyt do 12000 znaków z jawną
flagą częściowego zakresu. Notatki korzystają z istniejącego budżetu/tokenizera.
Oryginalny wycinek źródła ma do 1200 znaków. Anulowanie zamyka procesy.

Migracja 006 dodaje runs.allow_mcp (domyślnie 0), z istniejącym mechanizmem
kopii przed migracją. Stare wiadomości zachowują dotychczasowe znaczenie.
Kod: app/mcp_client.py, app/mcp_documents.py, scripts/mcp_docs_server.py.

## Potwierdzona weryfikacja Windows

Pełny dosłowny raport: MCP_TESTY.txt. Sprawdzono prawdziwe procesy stdio,
handshake/odczyt, zagnieżdżony Job Object, timeout, anulowanie, rozłączenie,
zły JSON/identyfikator/rozmiar, odmowę zapisu, brak tokenu w środowisku,
autoryzację ścieżek i sesji oraz obsługę zgody/źródeł w interfejsie.
Inference w automatycznych testach API jest atrapą i jest tak oznaczone.

Osobno rzeczywisty llama-server.exe CUDA z lokalnym Qwen3-8B wybrał mcp_docs,
odczytał docs/KOPIE_DZIENNIKA_GITHUB.md i zakończył odpowiedź ze źródłem.
311 znaków odpowiedzi; cała karta 7475/8192 MiB VRAM po generacji, kontekst
4096. To pojedyncza próba, nie gwarancja jakości każdej odpowiedzi.

Oficjalny SDK Python mcp 2.3.0 w oddzielnym środowisku QA (Python 3.14)
potwierdził oba kierunki: klient SDK → serwer KripAI oraz klient KripAI →
serwer SDK. Runtime aplikacji pozostaje CPython 3.13.17 bez zależności SDK.

## Następny zakres

Dowolne zewnętrzne serwery MCP, HTTP i OAuth nadal nie są wdrożone.
Kolejny konkretny moduł: jeden zewnętrzny dostawca stdio skonfigurowany lokalnie
przez właściciela, jawna lista narzędzi tylko do odczytu, przypięta tożsamość
programu i widoczny zakres zasobów. Odbiór musi objąć realny dostawca/odczyt,
rozłączenie, anulowanie, odmowę narzędzi zapisu i ochronę poświadczeń.
Samo wykonanie tools/list nie będzie uznane za ukończoną integrację.

Kontrakty: [transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[sesja](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[narzędzia](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
[SDK użyty w QA](https://pypi.org/project/mcp/2.3.0/).

Aktualizację zastosowano lokalnie po kopii programu i danych oraz sprawdzeniu
braku aktywnego generowania. Migracja 006 potwierdzona na rzeczywistej bazie
właściciela; backend i model gotowe. Z zainstalowanej kopii wykonano odczyt
docs/MCP.md; menu jest serwowane, katalog bez logowania zwraca 401.

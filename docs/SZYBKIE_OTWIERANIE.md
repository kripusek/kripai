# Ponowne otwarcie bez restartu modelu

03.11.2026. START.cmd rozpoznaje tę samą, już działającą instalację. Wtedy
otwiera jej stronę i pomija stop, rozpakowanie Pythona, instalację bibliotek,
testy i sprawdzanie pobrań. Otwieranie okna nie przerywa bieżącej rozmowy.

Sprawdzana jest blokada instancji, odpowiedź health/live i odcisk kodu
zapamiętany przy starcie backendu. Odcisk obejmuje app/, scripts/, web/, spec/
oraz główne pliki CMD. Porównujemy jednocześnie wersję uruchomioną, pliki
instalacji i katalog, z którego wywołano START. Zmiana plików po starcie
procesu nie jest uznawana za uruchomienie nowej wersji.

Brak odcisku, zmieniony kod, nieczynna instancja lub niepoprawna odpowiedź
powodują użycie dotychczasowej pełnej ścieżki. To przyspieszenie ponownego
otwarcia działającej aplikacji, nie skrócenie pierwszej instalacji ani zimnego
startu po restarcie Windows. Ładowanie CUDA nadal może potrwać; panel pokazuje
starting aż do gotowości modelu. Sama odpowiedź health/live oznacza backend.

Odcisk active-build.sha256 jest lokalną metadaną procesu w folderze danych;
nie zawiera kodu, rozmów, modelu ani kluczy. Odcisk nie zastępuje SHA pobrań
ani uprawnień Windows. Dowiązania/reparse, zbyt duże pliki i niepełna paczka
nie dopuszczają szybkiej ścieżki. Modele i runtime nie są haszowane przy
ponownym otwieraniu; odpowiedzialność za pobrania pozostaje w bootstrapie.
Próba liveness korzysta wyłącznie z localhost bez proxy i przekierowań.

Natywna próba PowerShell: 3.917 s, komunikat o ponownym otwarciu bez restartu,
identyczny PID llama-server przed/po, health/live 200. W tej próbie model
wciąż ładował się po aktualizacji — szybka ścieżka go nie przerwała.
Nie otwierano przeglądarki podczas tej próby; flagi -NoBrowser użyto w QA.
Sam wygląd desktop/mobile przeglądarki potwierdzono w poprzednim module.

Regresja Windows: 201 testów Python (200 OK, 1 symlink pominięty), Node 53/53.
Nowe testy: zmiana kodu/nazwy/locka, ignorowanie prywatnych danych, stara wersja
procesu mimo identycznie zmienionych katalogów, brak/niepoprawny odcisk,
brak blokady/serwera, obca odpowiedź, JSON/tablica/limit i odmowa redirectu.
Inference w tej regresji jest kontrolowane; SQLite/procesy prawdziwe.
Dosłowny raport: SZYBKIE_OTWIERANIE_TESTY.txt.

Kod: app/build.py, scripts/reuse_running.py, scripts/run.py, scripts/start.ps1.
Bez migracji/zależności i zmian uprawnień usług. Zwykły start nadal START.cmd.
Dalej: usprawnienie zimnego startu i zewnętrzny dostawca MCP. Ten moduł nie
zalicza mikrofonu PL/EN, ponownej pełnej instalacji ani uninstall.

03.11.2026: po aktualizacji model osiągnął ready. Osobna rzeczywista rozmowa
CUDA po starcie zwróciła poprawne 391 na 17×23 (asercja w QA), bez narzędzi.
Backend/model nadal dostępne w kolejnym poleceniu; nie deklarujemy czasu
inference jako benchmarku. Kopie kodu/danych wykonano przed aktualizacją.

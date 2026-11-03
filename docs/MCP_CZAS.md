# MCP: czas i strefy czasowe

Drugi konkretny zewnętrzny dostawca stdio: oficjalny **mcp-server-time
2026.10.28**, SDK **2.3.0**, protokół klienta **2025-11-25**. Wbudowana
dokumentacja i oficjalny filesystem działają nadal niezależnie. Ten moduł
odczytuje zegar systemowy i przelicza godzinę między strefami; nie jest
kalendarzem, harmonogramem ani obsługą dowolnego programu MCP.

W **+ → Połączenia → MCP · czas i strefy** kliknij **Przygotuj serwer czasu**.
Pierwszy raz pobieramy około16MB przypiętych wheels z publicznego PyPI.
Zależności są oddzielone od backendu, w program/runtime, a nie instalowane
do głównych bibliotek Pythona. Nie potrzeba systemowego pip, uv, Dockera,
WSL, konta ani tokenu. Runtime aplikacji pozostaje prywatnym CPython3.13 x64.
Gdy serwer jest gotowy, podaj np. Europe/Warsaw lub UTC i kliknij
**Test odczytu czasu**. Zobaczysz czytelną datę, godzinę, offset i link do
zapisanego wyniku. Test nie uruchamia modelu i działa też bez internetu.

W wiadomości włącz **MCP: dokumenty i czas**. Przykłady:

- „Która godzina w Warszawie? Odczytaj aktualny czas przez MCP”.
- „Przelicz dzisiaj 09:30 z Europe/Warsaw na America/New_York przez MCP”.

**Dodaj pytanie o czas** dopisuje pytanie do dokładnie zachowanego szkicu,
włącza MCP i przenosi fokus. Nie wysyła wiadomości. Zdjęcie trzeba odłączyć
samodzielnie; nie jest usuwane przez panel. Strefa wybrana do testu nie jest
zapisywana do konfiguracji. Domyślna strefa to Europe/Warsaw.

## Granice czasu i źródeł

Narzędzie `mcp_time`: action=now używa timezone; action=convert wymaga
timezone, target_timezone i time w HH:MM. Strefy są dokładnymi nazwami IANA.
Konwersja dotyczy **dzisiejszej daty w strefie źródłowej**, nie przyszłej daty
spotkania. Nie ma argumentu daty. Odrzucona przez dostawcę strefa/godzina
(np. godzina nieistniejąca przy zmianie zegara) daje jawny błąd.
Odczyt jest migawką; czas odpowiedzi modelu może być późniejszy. Źródło
zawiera moment odebrania wyniku i dane dostawcy. „Otwórz zapisany wynik”
pokazuje tę samą migawkę, zamiast odczytywać nowy zegar jako stary dowód.
Chroniona sesją trasa `/integrations/mcp-time/result?data=...` niesie wyłącznie
walidowane dane czasu w ograniczonym JSON/base64url. Nie zawiera tokenów,
ścieżek prywatnych ani uprawnień i nie uruchamia dostawcy przy otwarciu.

## Przygotowanie i granice procesu

32 wheels mają przypięte nazwy, rozmiary, URL i SHA256 w mcp-time-lock.json.
Brak wyszukiwania latest w runtime, skryptów budowania i wywołania pip.
Tylko HTTPS files.pythonhosted.org, brak proxy/przekierowań i kontrola hashy
przed rozpakowaniem. Inwentarz plików jest sprawdzany przed uruchomieniem.
Nieznany folder nie jest nadpisywany; znana poprzednia paczka jest zachowywana
przy naprawie. Promocja nieudana przywraca poprzedni katalog. Limit przygotowania
180s i anulowanie po odwołaniu sesji, bez długiej transakcji bazy.

MCP działa z minimalnym środowiskiem bez tokenów, stderr nie jest logowany.
Stały program/komenda, tylko get_current_time i convert_time, wymagane obie
adnotacje readOnlyHint. Nie ma metod zapisu, dowolnej ścieżki ani adresu usługi.
Job Object128MiBRAM,15s i standardowa ograniczona ramka stdio. Nadrzędny worker
35s/256MiB zamyka drzewo przy anulowaniu. To kontrola wybranego zaufanego
programu, nie systemowy sandbox dla dowolnego kodu administratora.
SDK i dane tzdata są używane w osobnym procesie; główny backend nie importuje SDK.
Licencje upstream pozostają w katalogach dist-info zainstalowanych wheels.

API: POST `/integrations/mcp-time/prepare` tylko owner +CSRF, POST `/test`
z typowanymi argumentami +CSRF/recheck sesji, GET `/result` tylko po logowaniu.
Brak nowej migracji: używamy dotychczasowego allow_mcp i SQLite źródeł.
Brak dodatkowego przełącznika na pasku. Moduł opcjonalny, reszta działa bez niego.

## Potwierdzone próby Windows

347 Python:346 zaliczonych,1 pominięty symlink; Node174/174. Nowe testy obejmują
rzeczywisty SDK/stdio, bieżący czas i konwersję, zabicie procesu/anulowanie,
rozłączenie, niezgodny/zbyt stary wynik, brak readOnly, błędne snapshoty,
sesję/CSRF/owner, hashe, obcy folder, zachowanie starego runtime i rollback
nieudanej promocji. Kontrolowane wheels instalatora nigdy nie są wykonywane.

Osobno prawdziwy zagnieżdżony worker odczytał czas i przeliczył09:30Warszawa
na03:30NowyJork w dacie próby03.11.2026. Rzeczywisty SDK miał55951360B pamięci
prywatnej w pojedynczym pomiarze, bez GPU. To nie gwarancja każdego zużycia.
Prawdziwy CUDA/Qwen3-8B wybrał mcp_time: odpowiedź77znaków zawierała dokładne
HH:MM dostawcy i właściwy cytat [W]; źródło zapisane. VRAM po odpowiedzi
7053/8192MiB, jeden pomiar. Konto i kontroler były testowe, inferencja rzeczywista.

Chromium/Playwright z prawdziwym API i SDK: czytelny wynik, chronione źródło
zgodne z odczytem, błąd Unknown/Zone, zachowany szkic/fokus/MCP bez autosend,
mobile390 bez overflow. W panelu messagesPOST0/model0. Bez produkcyjnego loginu,
nowego testu mikrofonu i prywatnych kont. Pełny raport: MCP_CZAS_TESTY.txt.

Kod: mcp_time.py, setup_mcp_time.py, mcp_time_server.py, mcp-time.js i rejestr.
START.cmd i Ctrl+F5. Źródła: [oficjalny pakiet](https://pypi.org/project/mcp-server-time/2026.10.28/),
[repozytorium dostawcy](https://github.com/modelcontextprotocol/servers/tree/main/src/time).

Rzeczywisty tokenizer: dwie migawki (now+convert) w przykładowym pytaniu zajęły
1707tokenów wejścia, zachowano oba źródła bez przycięcia. Kontekst4096,
rezerwacja wyjścia2048 i margines128 bez zmiany profilu GPU.

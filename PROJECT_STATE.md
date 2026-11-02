# KripAI — stan projektu
Aktualizacja: 03.11.2026. Ten plik opisuje bieżącą paczkę; STATUS.md zachowuje historię.

Aktualny zakres MCP i wyniki Windows: końcowy wpis „MCP stdio” oraz docs/MCP.md.
Starsze wyniki i ograniczenia poniżej opisują kolejne historyczne paczki.

## Aktualny etap
Etapy 1, 2 i 2.5a mają implementacje. Odbiór natywnego Windows nieukończony.
Etap 2.5b ma pierwszy działający zakres: tekstowy PDF → indeks E5/sqlite-vec
→ wybór dokumentów → pytanie w czacie → źródła ze stroną i wycinkiem.
Dokumenty skanowane i inne formaty nie są jeszcze indeksowane. Rozpoczęty moduł 4a: jawny odczyt WWW/publicznego GitHuba. Rozpoczęto też 4b: wyszukiwanie WWW i większe strony. Rozpoczęto 4c i ograniczony 4d; etapy 2.5c, 3 i 5–6 pozostają planem.

## Źródła i stan GitHub
Repo https://github.com/kripusek/kripai, main. Pierwsza publikacja źródeł:
f3d4b3180b31240443dee6df03c1a2e01e6e9024, po audycie ZIP i HANDOFF.
Bieżący zestaw zmian jest kontynuacją tego commita; wynik publikacji ustalać
z aktualnej historii GitHub, nie z dawnych wpisów audytu o samym README.
Właściciel polecił samodzielne sprawdzone pushe bez kolejnych pytań. Przed
aktualizacją gałęzi sprawdzać head, zachowywać nowszą pracę, bez force push.

## Zaimplementowane
- Logowanie/sesje, CSRF/Origin/Host, historia i migracje SQLite, idempotencja.
- SSE/replay/cancel, paginacja, tokenizer kontekstu, ostrzeżenie output_limit.
- Proces potomny llama-server, przełączanie tekst/VLM, Gaming, backup/restore.
- STT Whisper CPU i TTS System.Speech; PNG/JPEG/PDF oraz obraz w wiadomości.
- Markdown, MathML, kopiowanie kodu; nowe podstawowe kolorowanie oznaczonych bloków.
- START: prywatny Python i wheels z ZIP albo pobierane przy braku z kontrolą SHA.
- RAG tekstowych PDF: checkpoint strony, pauza/wznów/przebuduj, E5 CPU,
  filtrowanie owner+document w KNN, źródła w historii i spójne kopie wektorów.
Szczegóły i granice: README.md, spec/, docs/AUDYT_2026-11-02.md.

## Potwierdzone wyniki
Po poprawce dużych stron i 4b: 123 Python (119 OK, 4 pominięte Windows) i 43 JS OK; 162 zaliczonych.
Linux QA: Python 3.12.14, SQLite 3.53.1, sqlite-vec 0.1.6, FastAPI 0.115.12,
Pydantic 2.14.1, Pillow 12.3.0, pypdfium2 5.14.0. To nie jest runtime Windows.
W regresji: prawdziwe SQLite/vec0/PDF/procesy/HTTP, kontrolowane embeddingi/LLM.
Osobno: prawdziwy llama.cpp b12000 CPU + E5 Q8_0, 384 wymiary, poprawne top-1
w 3 małych przykładach PL/EN; prawdziwy dwustronicowy PDF zindeksowany i wyszukany.
To próby zgodności, nie pełne benchmarki ani potwierdzenie odpowiedzi GPU LLM.
Zweryfikowano Windows wheel/DLL i Linux wheel/SO przez SHA; model GGUF też pobrany
z poprawnym SHA. Pełny zapis: docs/WYNIKI_TESTOW.txt i docs/RAG_TESTY.txt.

## Nieweryfikowane / ograniczenia
NIE URUCHOMIONO: Windows 11, prywatny CPython 3.13.17 z Pydantic 2.11.3/Pillow 13,
instalacja/ACL/Job Object/uninstall, CUDA/VRAM, mikrofon i System.Speech PL/EN.
Nowy bootstrap PowerShell nie wykonany ani nie sparsowany natywnie — brak PowerShell.
Próba wizualnego testu Playwright zablokowana przez brak binarium przeglądarki.
Pobieranie z prawdziwego PyPI nie zostało wykonane (testy kontrolowanego HTTP).
Nowa DLL, embedding CPU i migracja 4 nie zostały wykonane na Windows.
Brak deklaracji pełnego audytu bezpieczeństwa lub gotowości produkcyjnej.

Znane ograniczenia: skończony kontekst 4096/wyjście 2048; jedno zdjęcie na wiadomość;
brak analizy dawnych pikseli bez ponownego załącznika, całodokumentowego OCR,
pamięci poza wybranymi tekstowymi PDF oraz narzędzi zapisu. Lekki lexer nie pokrywa pełnej gramatyki języków
(np. zagnieżdżonych szablonów); nieznane/duże bloki wyświetla jako zwykły tekst.
Licencja własnego kodu nadal niewybrana. Publiczne repo samo nie nadaje licencji.

## Ostatnie zmiany
web/syntax.js + integracja renderera i CSS: bez innerHTML/eval/CDN, limity kosztu,
zachowanie źródła i kopiowania, fallback przy błędzie/braku modułu.
scripts/downloads.py: brakujący wheel wybierany z PyPI po dokładnej nazwie i SHA;
adres HTTPS files.pythonhosted.org, sprawdzenie SHA przed rozpakowaniem.
scripts/start.ps1: brakujący ZIP prywatnego Pythona pobierany z przypiętego URL,
sprawdzenie SHA przed użyciem. Błędne istniejące pliki odrzucane, bez podmiany.
.gitignore wyklucza vendor/bazy/modele/binaria; ZIP zachowuje oryginalny vendor.
Poprawiono stare wzmianki o 768 tokenach w spec 02/05 i aktualne README.
Pierwszy moduł nie zmieniał bazy/modeli. W obecnym etapie doszła migracja 4
i model embeddingów CPU; nie zwiększono kontekstu modelu GPU.

## Następne zadania
1. Kontynuować zwykłe sprawdzone zmiany bez pytań o każdy push; aktualizować ten plik.
2. Windows / PowerShell: START.cmd i TESTY.cmd, potem Ctrl+F5. Osobno sprawdzić
   start z pełnego ZIP i czystych źródeł bez vendor; nie usuwać prywatnych danych.
3. Odbiór PL/EN, OCR, długiego kodu/kolorów/kopiowania, Gaming i pomiar VRAM,
   backup/restore/restart/uninstall według docs/INSTRUKCJA.md.
4. Dokończyć odbiór i jakość RAG zgodnie z nowym modułem opisanym poniżej.

## Decyzje architektoniczne
Windows natywnie, localhost:8765, SQLite WAL, llama.cpp CUDA, RTX 3060 Ti 8 GB,
jeden model GPU/jedna generacja, bez WSL/Docker/PostgreSQL/Caddy i płatnego API.
Dane/kopie poza programem; treść modelu/plików nie nadaje uprawnień.
Nie zwiększono kontekstu ani obciążenia VRAM. Dalsze decyzje: spec/DECISIONS.md.

## Ostatni moduł: RAG 2.5b
Nowe: app/vectors.py, embeddings.py, rag.py, web/rag.js, migracja 004-rag.sql,
scripts/rag-lock.json i testy RAG. Szczegółowy kontrakt: spec/etap-2.5b/RAG.md.
Instalacja: START.cmd pobiera E5 około 126 MiB; zależność sqlite-vec obowiązkowa.
Podczas testu rzeczywistego modelu wykryto brak token_type_count w GGUF;
jawny override odpowiada config E5 (2), przetestowany z b12000. Przestrzeń
indeksu identyfikuje model+kwantyzację+override; zmiana wymaga przebudowy.

Kolejne zadania: odbiór tego przepływu na Windows i pomiar RAM/VRAM; jakość
wyszukiwania PL/EN na większym zestawie; OCR skanowanych PDF/obsługa pustych
stron i innych formatów; potem resumable upload 2.5c. Cardputer i zdalna bramka
wymagają osobnego wdrożenia zgodnie ze specyfikacją, nie wystawienia localhost.

## Moduł 4a — internet i publiczny GitHub
Na wyraźne polecenie właściciela doprecyzowano plan internetu, wyszukiwarki,
konektorów/MCP i uprawnień zapisu. Szczegóły: spec/etap-4/INTERNET_WTYCZKI.md.
Kod 4a: app/network.py, tools.py, scripts/read_web.py, web/tools.js i migracja 5.
Brak nowych zależności/modeli; tekstowy llama-server otrzymuje --jinja.
Jawne flagi wiadomości; planer widzi tylko aktualną prośbę, do 2 odczytów.
WWW: wyłącznie wskazany HTTPS URL. GitHub: wskazane publiczne owner/repo,
README/issues oraz wyszukiwanie repo po fragmencie bieżącej wiadomości.
Kontrola DNS/IP/TLS/redirectów, GET bez sekretów/proxy/cookies, proces 18 s/256 MiB,
anulowanie/sesja/Gaming. Wyniki niezaufane, ograniczony kontekst i źródła w historii.

NIE POTWIERDZONO: rzeczywisty odczyt internetu na QA (tool_dns_failed w próbie
prawdziwego publicznego GitHuba); testy sieci są kontrolowane. Prawdziwy Qwen3-8B
z narzędziami na Windows, nowy proces/Job Object i wizualny UI niewykonane.
Raport: docs/INTERNET_TESTY.txt. Nie nazywać tego pełnym odbiorem etapu 4.

Następne zadania integracji: odbiór 4a na Windows, rozbudowa/odbiór 4b i dostawców wyszukiwarki WWW, 4c prywatne konta/adaptery/MCP i magazyn poświadczeń,
4d zapis w zakresie jawnych uprawnień właściciela. Tokeny ChatGPT nie są dostępne
lokalnemu KripAI. Pozostałe moduły z planu, w tym 2.5c i Cardputer, pozostają.

Baza publikacji modułu 4a sprawdzona na GitHub: 504559f52c70544df2a56efa19584c330b31307a.
Dokument nie zastępuje odczytu bieżącej gałęzi przed kolejnym pushem.

## Ostatni moduł — duże strony i wyszukiwanie 4b
Właściciel zgłosił działanie 4a poza większymi stronami i oczekuje funkcji bliższych
ChatGPT. Twardy limit 512 KiB dla web_read zastąpiono strumieniem do 8 MiB / 16 MiB
po dekompresji, wyciągiem do 160000 znaków i lokalnymi notatkami z fragmentów.
Jawne zakresy częściowe, oryginalne wycinki w historii. Sieciowe API/JSON nadal
mają limit 512 KiB. Protokół procesu do 1 MiB; proces 35 s/256 MiB.
Wyszukiwanie Bing RSS bez klucza, odczyt URL faktycznych wyników, 2 rundy i cache.
Nowe zapytania tylko przed wynikami sieci, aby strona nie wywołała eksportu query.
Bez nowych modeli/zależności/migracji. Poprzednie migracje pozostają niezmienione.

Próby prawdziwych danych przez trasę urllib QA: Wikipedia 1030701 B → 95312 znaków;
Bing RSS → 5 wyników. To nie potwierdzenie przypiętego transportu na Windows.
our-website-is-broken.org zwracał Site Unavailable — nie deklarować naprawy
samej zewnętrznej witryny ani obsługi logowania/CAPTCHA/JavaScript.
Raport: docs/WEB_SEARCH_TESTY.txt. Baza publikacji: d54c6c238f6986f671d231cd6abd6f029f6b6ff3.
Następnie odbiór nowego obiegu na Windows, dalsi dostawcy i jakość wyszukiwania,
4c własne konektory/MCP/prywatny GitHub; pozostałe moduły z planu zachowane.

## 02.11.2026 — pierwszy zakres integracji 4c
Dodano adaptery ReadAdapter WWW/GitHub, panel konfiguracji i test połączenia,
odczyt plików/katalogów domyślnej gałęzi oraz opcjonalny PAT szyfrowany DPAPI
CurrentUser z listą repozytoriów. Tylko GET; bez kont ChatGPT i zapisu usług.
Windows: 129/129 Python OK, 43 zachowania JS OK (Node: 44 pliki/testy).
Prawdziwy llama-server CUDA/Qwen3-8B wybrał narzędzie, odczytał publiczne README,
streścił fragmentami i odpowiedział; całkowity VRAM 7378/8192 MiB, kontekst 4096.
Bing RSS 5 wyników i odczyt python.org/doc potwierdzone. Wikipedia: błąd sieci.
DPAPI sprawdzono sztuczną wartością. Prywatne repo właściciela NIE URUCHOMIONO
(brak jego konfiguracji); wizualny UI i cancel rzeczywistej generacji do odbioru.
Start nadal START.cmd. Konfiguracja lokalna: scripts/configure-github.ps1.
Szczegóły, limity i następny konkretny zakres MCP: docs/INTEGRACJE_4C.md.
MCP pozostaje planem; bez nowych zależności, modeli ani migracji bazy.

## 02.11.2026 — odbiór właściciela i poprawka katalogów
Właściciel potwierdził panel integracji, cancel/Gaming i historię. Listy GitHub
zachowują teraz ścieżki bez streszczania LLM, z osobnym URL każdego katalogu.
Zajawki wyszukiwarki odróżniono od odczytu strony. Prawdziwy model CUDA zwrócił
17 plików app bez przypuszczeń; bezpośredni odczyt pathlib: 61453 znaki.
Bing RSS zwraca nietrafne wyniki pathlib — wyszukiwanie NIE ZALICZONE, wymaga
dalszej pracy nad dostawcą. Nie deklarujemy naprawy tego zewnętrznego problemu.
Windows: 130/130 Python OK i 43 zachowania JS OK (Node raportuje 44).
Instrukcja prywatnego repo i wyniki: docs/ODBIOR_INTERNETU_2026-11-02.md.
Prywatne konto właściciela nadal nieweryfikowane. Brak zmian bazy/modeli.

## 02.11.2026 — pierwszy 4d i automatyczna kontynuacja odpowiedzi
Właściciel polecił następny krok i naprawę ucinania odpowiedzi. Dodano
github_draft (lokalny diff po pełnym odczycie małego pliku) i panel tworzenia
nowej gałęzi/PR tylko w kripusek/kripusek-autoexec. Publikacja wymaga lokalnej
listy write_repositories i tokenu DPAPI; model nie dostaje narzędzia publikacji.
Kontrola SHA/head, owner/CSRF, trwały dziennik SQLite i blokada ślepych powtórek.
Tekst: do 8 automatycznych porcji po maks. 2048 tokenów, kontekst nadal 4096;
SSE/historia wspólne, korekta niepełnej linii, zachowanie tekstu po awarii.
Windows: 143/143 Python OK, Node 46/46 OK. CUDA: rzeczywiste 8 porcji po 128
tokenów dało zakończoną listę 30 punktów; prawdziwy README → lokalny draft PR.
Publikacji PR NIE URUCHOMIONO: odczyt skonfigurowany, ale zapis do autoexec
nie jest lokalnie włączony. Wizualny UI i długie VLM nadal do odbioru.
Struktura/start/limity/dług: docs/PR_I_DLUGIE_ODPOWIEDZI.md. Nowe generation.py,
github_changes.py, testy i panel; bez nowych zależności i zmiany profilu GPU.
Następnie konfiguracja zapisu/odbiór PR, kopie dziennika i uzgadnianie awarii,
kontynuacje VLM, MCP oraz trafniejszy dostawca WWW. Start: WYLACZ/START, Ctrl+F5.

## 02.11.2026 — zwykła odpowiedź przy włączonych narzędziach
Naprawiono tool_plan_limit dla zwykłej prośby o 50 wskazówek: planer ma
wybierać narzędzia, a nie pisać odpowiedź. Ucięty tekst bez tool_calls nie
blokuje właściwego generowania; niepełne wywołania nigdy nie są wykonywane.
Pusta lista wyników nie wymusza odpowiedzi ze źródeł ani odmowy ogólnych porad.
Windows: 146/146 Python i Node 46/46 OK. Regresja rzeczywistego HTTP/SSE/SQLite
obejmuje włączony Internet i GitHub, limit planera oraz brak wywołań sieci.
Rzeczywisty CUDA: planer dokładnej prośby właściciela zakończył się bez sieci.
Odtwarzalna próba pełnej odpowiedzi: scripts/verify_plain_advice.py.
Bez zmiany modeli, kontekstu, zależności i uprawnień. Start: WYLACZ/START, Ctrl+F5.

Pełnej listy 50 punktów na CUDA NIE UKOŃCZONO w tej próbie: model generował
bardzo wolno przy 100% obciążenia GPU (7421/8192 MiB). Potwierdzono przejście
planera bez sieci; nie deklarujemy odbioru wszystkich 50 punktów. Zatrzymano
wyłącznie własny proces verify_plain_advice.py, bez zatrzymywania backendu/modelu.

## 02.11.2026 — menu plus i lokalny kreator GitHuba
Stały pasek narzędzi zastąpiono menu + przy Wyślij; połączenia i propozycje PR
są w osobnym oknie. Kreator tworzy/testuje połączenie tokenem z poziomu UI,
Windows DPAPI, kopia przed zmianą/odłączeniem, bez tokenu w rozmowie/modelu.
Nie jest to OAuth: własna aplikacja GitHub nadal nieskonfigurowana.
Windows: 150/150 Python i Node 48/48 OK. Prawdziwy Chrome desktop/390 px
z kontrolowanym API: menu, zamykanie, formularz i układ bez poziomego przepełnienia.
Poświadczenia właściciela niezmienione; konto rzeczywiste NIE PODŁĄCZANE w teście.
Struktura/start/limity: docs/MENU_I_POLACZENIE_GITHUB.md. Nowe github_connect.py
i composer-menu.js. Start nadal WYLACZ/START, Ctrl+F5; bez modeli/zależności.
Następny moduł: odczytowe uzgadnianie niepewnego wyniku publikacji PR; potem
kopie dziennika, MCP i trafniejszy dostawca WWW. Użytkownik potwierdził działanie
poprzedniej poprawki planera/długiej odpowiedzi.

## 02.11.2026 — następny krok: sprawdzenie niepewnego PR
W oknie Połączenia dodano Sprawdź wynik w GitHub dla operacji o niepewnym
wyniku. Backend używa wyłącznie GET: parent, pliki/blob SHA/tryby, brak dodatkowych
zmian i zgodny PR. Rozróżnia potwierdzony PR, samą gałąź i brak potwierdzenia.
Nie odblokowuje ślepego ponowienia zapisu; owner i CSRF pozostają wymagane.
Windows: 153/153 Python i Node 49/49 OK. GitHub kontrolowany w regresji;
rzeczywistej publikacji/awarii konta właściciela NIE WYWOŁYWANO.
Szczegóły i dług: docs/UZGADNIANIE_PR.md. Struktura github_changes.py/API/panel;
bez nowych modeli, zależności i migracji. Start nadal START.cmd/Ctrl+F5.
Dalszy zakres: kopie dziennika, szersze edycje, OAuth z własną aplikacją, MCP
i trafniejszy dostawca WWW. Kreator lokalnego tokenu działa już bez PowerShella.

## 02.11.2026 — audyt działającej aplikacji na polecenie właściciela
Zweryfikowano aktualną lokalną instalację i rzeczywisty Chrome po lokalnym
logowaniu właściciela: menu +, Escape, połączenia i odpowiedź 391 działają.
Istniejące konto i dozwolone repo GitHuba: rzeczywiste GET OK. Zapis wyłączony.
Dodatkowo na odizolowanym SQLite/API z prawdziwym modelem: 391 przy włączonych
narzędziach, README ze źródłem, lokalny draft PR oraz pełne numery 1–50
w odpowiedzi 5245 znaków. Anulowanie po delta: cancelled, model nadal ready.
Domknięto wcześniejszą nieukończoną próbę pełnej listy 50 punktów.
Regresja Windows: 153/153 Python, Node 50/50 OK. Poprawiono niejasny status
read-only oraz stary komunikat odsyłający do PowerShella zamiast kreatora UI.
Dwa pliki UI wgrano też lokalnie po sprawdzeniu head i wykonaniu kopii; Ctrl+F5.
Nie zmieniono konta, haseł ani uprawnień. Nie publikowano PR; fizyczny głos,
VLM/RAG/uninstall i realny Gaming nie zostały ponownie odebrane w tej sesji.
Pełny raport i ograniczenia: docs/AUDYT_DZIALAJACEJ_APLIKACJI.md.
Rutynowe dostępne testy wykonuje agent samodzielnie; dalej PR po lokalnym
włączeniu zapisu, odbiór pozostałych modułów, kopie dziennika/MCP/WWW.

## 02.11.2026 — rzeczywista próba zapisu autoexec i obsługa odmowy
Właściciel autoryzował test gałęzi/PR w kripusek/kripusek-autoexec. Klucza
z rozmowy nie powielano ani nie utrwalano; zalecono lokalną konfigurację nowego.
Istniejące lokalne poświadczenie przeszło odczyt, ale GitHub odrzucił pierwsze
POST git/trees. Nie powstała gałąź ani PR; nie zmieniono main ani trwałych
uprawnień modelu. Propozycja README jest przygotowana i zachowuje grafiki/komendy.
Poprawiono rozróżnianie 401/403/limitów i jawnej odmowy przed pierwszą mutacją:
propozycja zostaje prepared do ręcznego ponowienia po konfiguracji. Błąd po
mutacji/utrata odpowiedzi nadal outcome_unknown. Brak automatycznych retry.
Windows: 156/156 Python i Node 50/50 OK. Rzeczywistej publikacji PR NIE ZALICZONO.
Szczegóły: docs/TEST_ZAPISU_GITHUB.md; dalej lokalne połączenie z Contents/Pull
requests write tylko dla autoexec i ponowny test. Kopie dziennika/MCP/WWW nadal
pozostają kolejnym zakresem. Start nadal START.cmd; bez nowych zależności/modeli.

## 02.11.2026 — kopie dziennika GitHuba i zachowawczy odzysk
BACKUP/start/kopia dobowa dołączają migawkę github-changes.sqlite3 oraz SHA
do kopii rozmów. Online Backup API z aktywnym WAL, samodzielne pliki DELETE,
walidacja schematu/danych/checksum, limit czasu/rozmiaru i retencja zestawów.
Restore scala dziennik: zachowuje nowsze rekordy i published, brakujące
nieopublikowane odzyskuje jako outcome_unknown bez zgody na ponowienie zapisu.
Stare kopie pozostawiają bieżący dziennik. Awaria/konflikt blokują zastąpienie
bazy. Wykryto i usunięto pozostawianie plików WAL/SHM kopii tymczasowej.
Windows: 167/167 Python i Node 50/50 OK. Rzeczywista kopia danych właściciela
z dziennikiem i SHA wykonana/zweryfikowana; danych właściciela NIE PRZYWRACANO.
Aktualizację zastosowano lokalnie po kopii plików programu i sprawdzeniu braku
aktywnego generowania. Backend oraz rzeczywisty model ponownie gotowe.
Struktura/start/limity: docs/KOPIE_DZIENNIKA_GITHUB.md, app/github_backups.py,
maintenance.py i test_github_backups.py. Bez nowych zależności/modeli/migracji.
Dalej: rzeczywisty PR po lokalnym udostępnieniu zapisu, MCP i trafniejszy WWW.
Klucza z rozmowy nie kopiowano do kodu/komend/logów; konfiguracja konta bez zmian.

## 02.11.2026 — MCP stdio: działający odczyt dokumentacji
Wdrożono osobny serwer MCP i klienta, zgodę w menu +, stan/test połączenia,
lokalne źródła wymagające sesji oraz migrację 006 (allow_mcp domyślnie 0).
Stałe narzędzia list_documents/read_document czytają tylko Markdown programu;
brak zapisu, dowolnych komend, kont i nowych zależności. Sekrety środowiska,
ścieżki spoza zakresu, symlinki/junction i żądania sampling są odrzucane.
Windows: 182 testy Python (181 OK, 1 symlink pominięty), Node 52/52 OK.
Pełne wyniki, struktura, limity i dalszy zakres: docs/MCP.md i docs/MCP_TESTY.txt.
Osobna rzeczywista próba CUDA/Qwen3-8B zakończyła odpowiedź ze źródłem MCP;
cała karta 7475/8192 MiB VRAM, kontekst 4096. SDK MCP 2.3.0 potwierdził
zgodność w obu kierunkach w oddzielnym środowisku QA, bez zmiany runtime.
Start nadal START.cmd. Dowolni zewnętrzni dostawcy MCP/HTTP/OAuth nadal planem.
Dalej: jeden zewnętrzny dostawca stdio z jawną listą narzędzi odczytu;
rzeczywisty PR autoexec nadal wymaga lokalnego udostępnienia zapisu.

Aktualizację zastosowano lokalnie po kopii programu i danych oraz sprawdzeniu
braku aktywnego generowania. Migracja 006 potwierdzona na rzeczywistej bazie
właściciela; backend i model gotowe. Z zainstalowanej kopii wykonano odczyt
docs/MCP.md; menu jest serwowane, katalog bez logowania zwraca 401.

## 02.11.2026 — trafniejsze wyszukiwanie dokumentacji Pythona
Odtworzono nietrafne odpowiedzi Bing RSS dla pathlib/site:docs.python.org.
web_search sprawdza teraz oficjalny indeks modułów przy pytaniu o dokumentację
Pythona: prawdziwe linki, dokładne nazwy/podmoduły i opcjonalna wersja 3.x.
Jawny dostawca wyniku; brak dopasowania/awaria pozostawia Bing RSS, a kod awarii
indeksu dociera do planera. Indeks nie jest udawanym odczytem treści dokumentu.
Windows: 186 testów Python (185 OK, jeden symlink pominięty), Node 52/52 OK.
Osobny rzeczywisty CUDA/Qwen3-8B wykonał wyszukanie i web_read oficjalnego pathlib,
odpowiedź completed ze źródłem, 1284 znaki; cała karta 7453/8192 MiB VRAM.
Kontekst 4096 i limity notatek zachowane. Bez migracji i nowych bibliotek.
Kod: app/network.py, app/tools.py, test_web_search.py; start nadal START.cmd.
Granice, dalsze zadania i raport: docs/DOKUMENTACJA_PYTHONA.md,
docs/PYTHON_DOCS_TESTY.txt. Ogólne WWW nadal zależy od wyników Bing/blokad stron;
zewnętrzni dostawcy MCP pozostają kolejnym osobnym zakresem.

Aktualizacja zastosowana lokalnie po kopii danych/programu i kontroli braku
aktywnego generowania. Backend i rzeczywisty model ponownie gotowe.
Z zainstalowanej kopii: znalezienie oficjalnego pathlib i odczyt 61453 znaków OK.

## 02.11.2026 — lokalne egzekwowanie site: w wyszukiwaniu WWW
Filtrowanie rzeczywistych hostów wyników: domena/poddomeny, -site:, IDNA,
granice DNS i przecięcie ograniczeń. Zakres z bieżącej prośby obowiązuje także
po pominięciu operatora przez model. Indeks Pythona respektuje domenę.
Puste wyniki pozostają puste; metadane liczby odrzuconych trafiają do planera.
Niepoprawny filtr ma czytelny błąd przed połączeniem. Bez migracji/zależności.
Windows: 190 testów Python (189 OK, 1 symlink pominięty); Node 53/53 OK.
Rzeczywisty transport znalazł pathlib w docs.python.org; przy example.org
odrzucił wszystkie 10 obcych wyników RSS mimo braku site: w query modelu.
Kod: app/network.py, app/tools.py, web/tools.js; start nadal START.cmd.
Kontrakt, ograniczenia i odbiór: docs/FILTR_DOMEN_WWW.md, docs/SITE_FILTER_TESTY.txt.
Dalej: jakość ogólnego WWW i zewnętrzny dostawca MCP; nie zaliczono wszystkich
stron, instalatora i mikrofonu PL/EN. Brak zmian uprawnień kont/GitHuba.

Osobny rzeczywisty CUDA/Qwen3-8B wykonał wyszukiwanie z site:docs.python.org,
odczytał pathlib i zakończył odpowiedź ze źródłem (614 znaków). Cała karta
7575/8192 MiB VRAM; kontekst nadal 4096.

Aktualizacja zastosowana lokalnie po kopii danych/programu i kontroli braku
aktywnego generowania. Backend i rzeczywisty model ponownie gotowe.
Zainstalowana kopia: oficjalny wynik poprawny, 10 obcych wyników odrzuconych
przy zakresie example.org, health/live 200. Bieżący schemat 6 bez migracji.

## 02.11.2026 — czarno-czerwony motyw i przekierowania site:
Motyw na polecenie właściciela: grafitowe tło, czerwone akcenty/monogram,
bezszeryfowe nagłówki, ciemne logowanie/dialogi/menu +, źródła i kod.
Lokalny theme.css ładowany po bazowym CSS, bez fontów/CDN i nowych zależności.
Inspiracje sprawdzone w publicznym profilu/repo kripusek; paleta wynika
z bieżącego polecenia właściciela, nie z deklaracji identyczności starej strony.
Filtr site: wyniku wyszukania obejmuje każdy redirect, z odmową przed DNS
i połączeniem poza domenę. Osobny URL właściciela zachowuje własną zgodę.
Windows: 192 testy Python (191 OK, 1 symlink pominięty), Node 53/53 OK.
Chrome headless: desktop/390px, logowanie, menu, dialog i odpowiedź; bez
poziomego przepełnienia. API tego podglądu kontrolowane; nie test konta owner.
Lokalnie po kopii programu/danych przywrócono gotowość backendu/modelu;
schemat 6 bez nowych migracji. Wcześniejsza próba CUDA przerwana z
inference_interrupted przy modelu offline; nie została zaliczona jako sukces.
Start nadal START.cmd. Dalej: zewnętrzny MCP i odbiór pozostałych modułów.
Szczegóły i dosłowna regresja: docs/MOTYW_KRIPUSEK.md i docs/MOTYW_TESTY.txt.

## 02.11.2026 — trwały start backendu z launchera Windows
Ustalono przyczynę znikania aplikacji po poleceniach agenta: backend dziedziczył
nadrzędny Windows Job i był zamykany wraz z sesją narzędzia. manage.py uruchamia
teraz backend z CREATE_BREAKAWAY_FROM_JOB. Przy odmowie Windows (winerror 5)
zachowuje zwykły start; inne błędy nie są maskowane. Job modelu i ograniczenia
procesów narzędzi pozostają w backendzie. Bez nowych usług/zależności/migracji.
Windows: 196 testów Python (195 OK, 1 symlink pominięty), Node 53/53 OK.
Osobny rzeczywisty proces backendu przeżył koniec polecenia uruchamiającego;
CUDA/Qwen3-8B zakończył wyszukanie/odczyt pathlib ze źródłem (1107 znaków),
cała karta 7359/8192 MiB VRAM. Kontekst 4096. Wcześniejsze przerwane próby
zachowano jako niezaliczone. Weryfikacja zwykłego manage.py: raport końcowy.
Motyw czarno-czerwony działa lokalnie; start nadal START.cmd, Ctrl+F5 odświeża UI.
Pełny raport: docs/MOTYW_TESTY.txt. Dalej: poprawa zwykłego startu oraz MCP.

Zwykłe zainstalowane manage.py stop/start przeszło po kopii kodu i danych.
W osobnym kolejnym poleceniu health/live oraz chronione v1/models dały 200;
backend i model przeżyły zakończenie launchera. Nie trzeba skryptu pomocniczego.

## 03.11.2026 — szybkie ponowne otwarcie działającej aplikacji
START porównuje odcisk uruchomionego kodu z instalacją i katalogiem źródłowym.
Przy zgodności, aktywnej blokadzie i poprawnym health/live otwiera stronę bez
stop/reinstalacji/testów/pobrań. Brak/zmiana/stara wersja procesu oznacza pełną
dotychczasową ścieżkę. Odcisk nie obejmuje modeli/danych/poświadczeń i nie
zastępuje SHA pobrań. Lokalna meta active-build.sha256, bez migracji/zależności.
Windows: 201 testów Python (200 OK, 1 symlink pominięty), Node 53/53 OK.
Rzeczywisty PowerShell START -NoBrowser: 3.917 s, PID modelu bez zmiany,
backend live. Model podczas tej próby jeszcze się ładował; nie przerwano go.
To nie przyspieszenie zimnego startu ani ponowny test pełnego instalatora.
Struktura/limity/dalej: docs/SZYBKIE_OTWIERANIE.md; pełny raport obok.
Start nadal START.cmd. Dalej: zimny start i zewnętrzni dostawcy MCP.

03.11.2026: po aktualizacji model osiągnął ready. Osobna rzeczywista rozmowa
CUDA po starcie zwróciła poprawne 391 na 17×23 (asercja w QA), bez narzędzi.
Backend/model nadal dostępne w kolejnym poleceniu; nie deklarujemy czasu
inference jako benchmarku. Kopie kodu/danych wykonano przed aktualizacją.

## 03.11.2026 — GitHub: gałęzie i odczyt wskazanej rewizji
github_read obsługuje branches (20 wyników + jawny limit) oraz opcjonalny ref
dla README/pliku/katalogu. Źródła zachowują gałąź/tag/SHA zamiast wskazywać HEAD.
Plik z jawnego ref nie daje editable ani zgody na draft bieżącej gałęzi.
Repo nadal musi być w bieżącej prośbie; brak nowych uprawnień/tokenów/zapisu.
Windows: 206 Python (205 OK, 1 symlink pominięty), Node 53/53. Rzeczywisty
anonimowy proces: lista gałęzi, README i app przy SHA 60c504b poprawne.
Kod: app/tools.py, app/network.py, test_github_refs.py; brak migracji/deps.
Start START.cmd. Szczegóły/raport: docs/GITHUB_REWIZJE.md i plik TESTY obok.
Dalej: przegląd PR tylko do odczytu oraz zewnętrzni dostawcy MCP.

Natywna próba wykryła 30-sekundowy ReadTimeout planera w profilu f16.
Profil tekstowy używa teraz Flash Attention on oraz KV K/V q8_0 (bez zmiany
GGUF/kontekstu 4096/wyjścia 2048). Flagi sprawdzone w lokalnym b12000 --help.
Po zmianie rzeczywisty CUDA/Qwen3-8B odczytał wskazany commit i zakończył
odpowiedź ze źródłem (452 znaki). Start modelu w próbie 5.248 s, cała karta
7322/8192 MiB po odpowiedzi. Nie jest to benchmark jakości ani dowód przyczyny
każdego timeoutu. Model VLM zachowuje własny dotychczasowy profil.

Dodatkowo prawdziwy Qwen3-8B z q8 KV: poprawne 391 na 17×23; generacja
przerwana po rzeczywistej delcie, run=cancelled, model pozostał gotowy.
Kontroler trybu i konto w tych próbach były odizolowanymi fixture, inference
i CUDA rzeczywiste. Nie zatrzymywano modelu właściciela przez Gaming.

## 03.11.2026 — odczyt PR, opisów i patchy
github_read pulls/pull: lista otwartych PR i konkretny numer, również zamknięty.
Metadane → pliki → metadane sprawdzają spójność head/base SHA. Jawne limity
20 plików/6000 znaków patcha/2000 opisu, binary/brak diff/512 KiB API.
Nazwy typowych sekretów blokują odczyt/patch także po rename. PR nie nadaje
editable ani uprawnień zapisu. W kreatorze nowego PAT odczyt PR, bez zmiany
istniejącego tokenu; prywatny PR wymaga Pull requests: Read-only.
Windows: 213 Python (212 OK, 1 symlink pominięty), Node 55/55. Prawdziwy proces
anonimowy: kripai pulls=0, python/cpython #158469 odczytany częściowo. Bez zapisu.
Nowe prywatne konto NIE URUCHOMIONO. Start START.cmd, brak migracji/deps.
Kod app/github_pulls.py, network/tools i UI. Kontrakt/raport:
docs/GITHUB_PR_ODCZYT.md i GITHUB_PR_ODCZYT_TESTY.txt. Dalej: panel GPU/MCP.

Osobno CUDA/Qwen3-8B q8 KV odczytał PR python/cpython #158469 i zakończył
odpowiedź ze źródłem (1106 znaków). Cała karta 7187/8192 MiB po próbie.
To test przepływu i źródła, nie gwarancja trafności każdej recenzji.

## 03.11.2026 — rzeczywisty pomiar VRAM w panelu systemu
GET system/gpu (sesja/Host) i nowy web/gpu.js: całe karty NVIDIA, used/total/free,
czas próbki, kontekst i limit porcji. Stały nvidia-smi w systemowych lokalizacjach,
tylko query, timeout 3 s, cache 5 s, limit wyjścia/kart. Brak sterownika/błąd
nie udają zera wolnego VRAM. Wylogowanie odrzuca spóźniony pomiar.
Windows: 217 Python (216 OK, 1 symlink pominięty), Node 58/58. Rzeczywista
RTX 3060 Ti przez API fixture: 7038/8192 MiB zajęte i 987 wolne. Chrome desktop/
390px sprawdzony z kontrolowanym API zasilonym rzeczywistą próbką.
To cała karta, nie tylko model ani gwarantowany budżet WDDM. Inference regresji
kontrolowane; konto fixture, bez użycia hasła owner. Start START.cmd, brak deps/
migracji. Kod app/gpu.py/main.py i web/gpu.js. Kontrakt/raport docs/PANEL_GPU.md
oraz PANEL_GPU_TESTY.txt. Dalej: mobilna nawigacja i zewnętrzny MCP.

## 03.11.2026 — pełna szerokość rozmowy na telefonie i stan sesji
Historia do 700 px wysuwana spod menu; Escape/tło, Tab i przywracanie fokusu,
inert tła, reset po resize/logout. Komputer zachowuje stałą historię.
Lista rozmów i wiadomości czyszczone po logout; stare me/lista/401 nie
odtwarzają starego widoku i nie wylogowują nowej sesji. Bez zmiany serwerowej
autoryzacji i przechowywania sekretów. Wyślij czeka na aktualny stan modelu.
Windows: 217 Python (216 OK, 1 symlink pominięty), Node 65/65. Chrome desktop/
390 px: main 390/390, role/fokus/Shift+Tab/Escape, ustawienia i brak overflow.
API podglądu kontrolowane, bez hasła owner. Kod sidebar.js/app.js/HTML/CSS,
bez deps/migracji; start START.cmd i Ctrl+F5. Szczegóły/raport:
docs/MOBILNA_NAWIGACJA.md i MOBILNA_NAWIGACJA_TESTY.txt. Dalej: zewnętrzny MCP.

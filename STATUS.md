# STATUS — 30.10.2026, Windows native

## Zrobione
Etap 1 przeniesiony na SQLite WAL i backend Windows. Wycofano zależności
WSL/Docker/PostgreSQL/Caddy. Login, CSRF, sesje, historia, SSE replay, cancel,
idempotencja i izolacja właścicieli zachowane. Model jako proces potomny z
Windows Job Object, automatyczny Gaming. Prywatny Python i przypięte wheels,
manifesty SHA serwera CUDA i modelu. START/WYLACZ, backup/restore/reset/uninstall,
import historii starego panelu. Długi czat: keyset pagination i tokenizer budget.
Plan etapów 2–6 przepisany na Windows i RAG sqlite-vec. Na kolejne polecenie
właściciela rozpoczęto etap 2 — szczegóły poniżej.

## Struktura
app/ — API, SQLite, kontekst, proces modelu, hasła i kopie.
scripts/ — instalator PowerShell, start/stop, download, import, test runner.
tests/ — rzeczywisty SQLite/API/SSE/procesy, awarie, import, archiwa i checksum.
web/ — interfejs bez frameworka; vendor/ — przypięty Python/wheels z licencjami.
spec/ — obowiązujący plan, SQLite SQL i OpenAPI; docs/ — wyniki i źródła.

## Uruchomienie i wersje
Windows: START.cmd; adres http://localhost:8765. WYLACZ.cmd kończy program.
CPython 3.13.17, FastAPI 0.115.12, Pydantic 2.11.3, httpx 0.28.1, uvicorn 0.34.2.
SQLite według runtime (raport testów). llama.cpp b12000 CUDA 12.4 x64,
Qwen3-8B Q4_K_M (rewizja i SHA w scripts/model-lock.json), kontekst 4096.

## Testy / znane ograniczenia
Dosłowne wyniki: docs/WYNIKI_TESTOW.txt. Uruchomiono testy na Linux z prawdziwym
SQLite, serwerem HTTP atrapą inference i prawdziwymi procesami potomnymi.
NIE URUCHOMIONO: instalator/ACL/private Python na Windows, CUDA, VRAM,
Windows Job Object, przeglądarka wizualna i odinstalowanie na Windows.
Instalator uruchamia ten sam zestaw testów na Windows przed pobraniem modelu.
Nie wykonano commita: warunek pełnych zielonych testów natywnych nie został spełniony.
Bez push, deploy i podłączania kont zewnętrznych.

## Uproszczenia / dług / następny krok
Brak automatycznej migracji woluminu PostgreSQL — opcjonalny import wymaga
chwilowo działającego starego panelu. Nie przenosimy starych sesji/runów.
Nie ma streszczania ani nieograniczonej pamięci; starsze tury poza kontekstem
pozostają dostępne w historii. Jedna generacja i jeden backend; SQLite nie
jest serwerem wielomaszynowym. Kopie lokalne nie zastępują kopii na innym dysku
ani szyfrowania. Brak globalnego autostartu i automatycznych aktualizacji zależności.
Przed zamknięciem etapu: test checklist README na docelowym Windows, w tym
awaria backendu, VRAM, backup/restore i bezpieczne odinstalowanie. Potem commit.

## Wynik ostatniej weryfikacji
Końcowy wynik etapu 2.5a: patrz nowa sekcja poniżej i docs/WYNIKI_TESTOW.txt.
Parser PowerShell 7.6.9 na Linux: wszystkie trzy skrypty poprawne.
JavaScript i Python: kontrola składni OK.
Wszystkie pliki vendor zgodne z SHA-256; prywatny Python zawiera SQLite.

## Etap 2 — wstępny moduł głosu (30.10.2026)
Zrobione: nagrywanie przyciskiem do 30 s (AudioWorklet), konwersja do WAV,
transkrypcja lokalnym Whisper CPU do pola korekty, odczyt odpowiedzi przez
System.Speech, wybór PL/EN, anulowanie i powiązanie z Gaming/wylogowaniem.
Procesy z timeoutem i Job Object, pliki prywatne/usuwane, brak treści w argv
i logach. Powtórne UUID i anulowanie przed startem chronią przed wyścigami.

Nowe pliki: app/voice.py; scripts/speak.ps1 i voice-lock.json; web/voice.js,
pcm.js i recorder-worklet.js; tests/test_voice.py i test_voice_ui.cjs;
spec/etap-2/GLOS.md. Zaktualizowano START, API, UI, OpenAPI, README i źródła.

Start w Windows nadal START.cmd, potem Ctrl+F5. Dodatkowe pobranie ~497 MB.
Whisper.cpp b5454, model small wielojęzyczny, 4 wątki CPU, bez CUDA dla głosu.
System.Speech używa lokalnych głosów Microsoft, nie jest otwartym modelem TTS.
Brak głosu oznacza czytelny błąd; nie zmieniamy rejestru/nie używamy cloud.

Rzeczywisty test EN przez API: 11 s oficjalnego nagrania → poprawna oczekiwana
fraza, ok. 3,41 s w Linux QA. Audio usunięte, brak automatycznej wiadomości.
To nie benchmark Windows ani ocena polskiego. Testy UI używają kontrolowanych
obiektów przeglądarki; nie zastępują mikrofonu i fizycznego odtwarzania.

Dług: jakość small PL, finalny dobór profilu, dostępność głosów System.Speech,
RAM/czas na Windows, test przeglądarki z mikrofonem i odbiór offline PL/EN.
Nagrywanie włącza/wyłącza kliknięcie (nie stały nasłuch), brak VAD i ciągłego
STT; ciche nagranie może dać błędną transkrypcję — właściciel sprawdza tekst.
Odczyt max. 12000 znaków, kolejne porcje do 1200. Nie ma trwałych zadań głosu.
Następny krok: odbiór etapu 1 i głosu na Windows według README, ewentualne
poprawki jakości. Właściciel następnie potwierdził działanie bota i polecił kolejny etap. Brak commita: nadal nie
spełniono warunku pełnych zielonych testów natywnych. Bez push i deploy.

## Korekta STT po zgłoszeniu właściciela
Whisper base przekręcał polskie słowa i nazwy HTML/CSS/JavaScript. Zmieniono
profil na small wielojęzyczny, SHA w voice-lock.json, nowy plik ggml-small.bin.
START pobiera około 488 MB przy aktualizacji. Backend nie wraca cicho do
starego base, a brak nowego modelu zgłasza błąd. Stary plik nie jest usuwany.
Nie stosujemy słownikowych zamian ani generatywnego poprawiania wypowiedzi.

Test wyboru modelu i awarii braku small: zaliczony. Wszystkie testy: 49 Python
+ 8 JS zaliczonych, 3 Windows pominięte. Rzeczywisty small CPU EN: 11 s nagrania
rozpoznane w 4,73 s na Linux QA (nie benchmark sprzętu właściciela).
NIE URUCHOMIONO: to samo nagranie PL właściciela — nie mamy pliku audio.
Następny krok: Windows START, Ctrl+F5, język Polski i ponowienie wypowiedzi
o stronie do sprzedaży gofrów; porównać słowa oraz czas. Większy model może
być wolniejszy. Poprawa dokładności tego konkretnego zdania niepotwierdzona.

## Etap 2.5a — PNG/JPEG/PDF i model obrazu (30.10.2026)
Zrobione: upload z limitem i kontrolą rzeczywistego formatu, prywatny podgląd,
wybór strony PDF, warstwa tekstowa, OCR generatywny i pytania o obraz.
Ręczne wstawianie wyniku do wiadomości, bez wysyłania automatycznego.
Anulowanie/Gaming/wylogowanie, ACL plików, timeout, limit pamięci dekodera.
Jeden proces modelu: tekst → VLM → tekst, zatrzymanie starego przed nowym.
Załączniki w SQLite BLOB, migracja 2 z kopią przed zmianą, restore wersji 1/2.
Usuwanie z kopią przed operacją; starsze kopie mogą zawierać usunięte dane.

Nowe pliki: app/media.py, scripts/decode_media.py, scripts/vision-lock.json,
web/media.js, tests/test_media.py, tests/test_media_ui.cjs,
spec/etap-2.5a/002-pliki.sql i PLIKI.md. Zmiany w migracjach/kopiach,
kontrolerze procesu, instalatorze, API/OpenAPI, UI, testach Windows i dokumentacji.

Wersje: Pillow 13.0.0, pypdfium2 5.14.0, Qwen3-VL-4B-Instruct Q4_K_M
Unsloth + mmproj F16, przypięta rewizja 00c00da0690c4b14b5539b02c4ea5d7c9102b35e.
Serwer nadal llama.cpp b12000. Projektor CPU, jeden slot, kontekst 4096,
limit obrazu 1024 tokeny. Zależności Windows w paczce; model pobierany osobno.
Start Windows: START.cmd z nowej paczki, potem Ctrl+F5. Dodatkowe 3.34 GB.

Końcowe testy: 66 Python — 62 zaliczone, 4 pominięte Windows; 13 JavaScript
zaliczonych. Razem 75 zaliczonych i 4 pominięte. Dosłowny raport w docs.
Rzeczywisty Qwen3-VL na CPU Linux odczytał KRIPAI TEST 123 przez media.ask_model.
To osobna próba rzeczywistego modelu; testy automatyczne inference używają atrap.
Zweryfikowane SHA vendor/modeli, składnia JS/Python/PowerShell i OpenAPI.
NIE URUCHOMIONO: CUDA/VRAM/instalator/Job Object na Windows i wizualny test UI.
Brak commita: pełne zielone testy natywne nadal niewykonane. Bez push/deploy.

Uproszczenia/dług: jeden dekoder i jedna strona na analizę, do 8 MiB,
50 plików/200 MiB, 16 mln pikseli obrazu, 50 stron PDF, wynik do 12000 znaków.
Nie ma RAG, pamięci dokumentów, sandboxa dekodera ani gwarancji bezbłędnego OCR.
Wyniki pochodzą z podglądu do 1024 px; drobny tekst może wymagać wycinka obrazu.
Pobrania i modele nie są częścią ZIP. Następny krok: checklist Windows w README,
odbiór jakości PL/EN/OCR i pomiar VRAM; potem etap 2.5b RAG sqlite-vec.

## Aktualny moduł — 02.11.2026 — zdjęcia w czacie i formatowanie
Odtworzono na zapisanej wersji 10 po utracie niezapisanych plików poprzedniej
sesji. Wyniki wcześniejszej niezapisanej pracy nie są wynikami tej paczki.
Zrobione: Ctrl+V/przeciąganie/wybór zdjęcia, miniatura, wspólne wysłanie pytania,
SSE i obraz w historii, cancel/wylogowanie i idempotencja. Markdown, bloki kodu
z kopiowaniem, tabele, listy, cytaty, podstawowy MathML. Kod odpowiedzi nie wykonuje się.

Nowe: web/attachments.js, web/format.js, web/vendor/marked, scripts/web-vendor-lock.json,
spec/etap-2.5a/003-obraz-w-rozmowie.sql i CZAT.md; tests/test_chat_images.py,
test_chat_ui.cjs, test_format_ui.cjs, dom.cjs. Zmiany worker/API/UI/migracji i dokumentacji.
Wersja Marked 17.0.5 MIT, pobieranie bibliotek niepotrzebne. Modele/Python bez zmian.
Windows: START.cmd → Ctrl+F5. Kopia przed migracją 3, dane i hasło zachowane.

Testy tego przebiegu: 71 Python = 67 OK + 4 pominięte Windows; 27 JavaScript OK.
Łącznie 94 zaliczone, 4 pominięte. Prawdziwy SQLite/dekodery/procesy, VLM jako atrapa.
Linux QA: Pillow 12.3.0 i pypdfium2 5.14.0 dostępne lokalnie. Windows vendor ma
Pillow 13.0.0; jego natywnego wykonania NIE URUCHOMIONO, tylko sprawdzono SHA.
NIE URUCHOMIONO: Windows/CUDA/VRAM, mikrofon oraz wizualny test przeglądarki.
Brak commita: pełne zielone testy natywne nadal niewykonane. Bez push/deploy.

Dług: jedno zdjęcie na wiadomość; brak pamięci dawnych pikseli; ograniczony TeX,
bez kolorowania kodu. Anulowany upload może pozostać w panelu plików.
Następny krok: ręczny odbiór Windows z README, następnie planowany RAG sqlite-vec.

## 02.11.2026 — cutoff odpowiedzi
Przyczyna potwierdzona w kodzie: limit 768 i brak odczytu finish_reason. Zwiększono
OUTPUT do 2048 w config.py i żądaniach tekst/VLM. Kontekst nadal 4096; mniejszy
budżet wejścia może wcześniej odrzucić pojedyncze długie pytanie. Historia zostaje.
Odpowiedź ograniczona długością zapisana w historii z output_limit w run/SSE,
UI ostrzega; Kontynuuj wstawia końcowe 2000 znaków do nowej prośby do edycji.
Panel plików również ostrzega o truncated. Brak nowych bibliotek/modeli/migracji.
Pliki: app/config.py, main.py, media.py, web/app.js, media.js; test_cutoff.py,
test_chat_ui.cjs, dokumentacja. Start: Windows START.cmd, potem Ctrl+F5.
Testy: 76 Python (72 OK, 4 Windows pominięte), 29 JS OK = 101 zaliczonych,
4 pominięte. Rzeczywisty HTTP/SSE i SQLite, kontrolowany model, bez testu CUDA.
NIE URUCHOMIONO: Windows/GPU oraz wizualny test przeglądarki — brak środowiska.
Brak commita/push/deploy: pełne zielone testy natywne nadal nie zostały wykonane.
Ograniczenia: skończony budżet; Kontynuuj nie gwarantuje idealnego sklejenia kodu.
Następny krok: sprawdzenie długiego kodu i ostrzeżenia na docelowym Windows.

## 02.11.2026 — przygotowanie repozytorium i README
Na polecenie właściciela uporządkowano README: funkcje zaimplementowane, plan
etapów, zadania niewykonane, start, modele/limity, dane, bezpieczeństwo i wyniki.
Poprzednią szczegółową instrukcję zachowano bez zmian jako docs/INSTRUKCJA.md.
Właściciel jawnie autoryzował pierwszy commit/push; odnotowano w AGENTS.md,
bez uznawania brakujących testów Windows za zaliczone. Kod wykonawczy bez zmian.
GitHub: dostępne repozytoria nie obejmują KripAI; integracja nie ma operacji
utworzenia repozytorium. Push NIE WYKONANY — potrzebny docelowy adres repo
udostępnionego integracji. Nie wysłano projektu do innego repozytorium.
Następny krok: utworzenie/udostępnienie prywatnego kripusek/KripAI, pierwszy push.

Weryfikacja przygotowania repo: wszystkie testy ponownie uruchomione — 76 Python
(72 OK, 4 Windows pominięte) i 29 JavaScript OK. Linki README i przyciski istnieją;
stara instrukcja zachowana dosłownie. .gitignore rozszerzony o warianty .env,
modele, kopie i katalogi tymczasowe. 112 plików przejrzanych do pierwszego commita,
bez prywatnych danych/runtime/modeli; suma zależności bez zmian. Pierwszy commit
lokalny przygotowany na jawne polecenie właściciela; push nadal NIE WYKONANY.

## 02.11.2026 — odzyskanie, audyt i pierwszy moduł kontynuacji
Bieżący stan: PROJECT_STATE.md; audyt: docs/AUDYT_2026-11-02.md.
GitHub main 65667aab5d5da25fbdf77b2f947786f560801a8e zawiera tylko README,
identyczny z wejściowym README ZIP. Starsze wpisy o braku dostępu są historyczne.
Dodano podstawowe lokalne kolorowanie kodu, testy awarii/fallbacku/kopiowania.
Wykluczono binarne vendor z Gita; START obsługuje brakujący Python (stały URL/SHA),
a downloads.py brakujące wheels przez PyPI z dokładną nazwą/SHA.
Testy: 81 Python = 77 OK + 4 Windows pominięte, 33 JS OK; razem 110 OK.
QA Linux: Python 3.12.14, SQLite 3.53.1, Pydantic 2.14.1, Pillow 12.3.0;
Windows lock pozostaje CPython 3.13.17, Pydantic 2.11.3, Pillow 13.0.0.
Nie wykonano testów Windows/CUDA ani nowej ścieżki instalatora na Windows.
Próba Playwright: brak zainstalowanej przeglądarki, wizualny odbiór niewykonany.
RAG nadal planem. Push niewykonany: aktualne polecenie wymaga zatwierdzenia zakresu.

## 02.11.2026 — zgoda na samodzielne pushe
Właściciel polecił wykonywać sprawdzone zwykłe pushe bez kolejnych zatwierdzeń.
Zaktualizowano AGENTS/PROJECT_STATE i zakres synchronizacji. Zgoda obejmuje
pierwszy import źródeł; nie zmienia brakujących testów Windows/CUDA ani zasad
zachowania nowszej pracy. main przed publikacją nadal wskazuje 65667aab.

## 02.11.2026 — RAG 2.5b, pierwszy zakres
Zaimplementowano tekstowe PDF, sqlite-vec 0.1.6 i E5-small Q8_0 CPU. Migracja 4
z kopią, checkpoint strony, pauza/wznów, usuwanie pochodnych, backup wektorów
i filtr owner+document wewnątrz KNN. Wybór PDF w panelu i źródła w historii.
Nowe moduły app/vectors.py, embeddings.py, rag.py, web/rag.js, rag-lock.json,
004-rag.sql i testy RAG. Szczegóły: spec/etap-2.5b/RAG.md oraz PROJECT_STATE.md.
Testy: 96 Python (92 OK, 4 Windows pominięte), 39 JS OK = 131 zaliczonych.
Rzeczywisty E5 CPU b12000 oraz PDF→vec0→wyszukiwanie na Linux potwierdzone;
3 proste przykłady PL/EN nie są benchmarkiem. Testy regresji modeli używają atrap.
Natywny Windows/CUDA/VRAM/nowa DLL/instalator i wizualny UI niewykonane.
Start Windows: git pull --ff-only, START.cmd, Ctrl+F5. Dodatkowe pobranie około
126 MiB; istniejące rozmowy zachowane. Brak OCR skanów i innych formatów w RAG.

## 02.11.2026 — internet i integracje 4a
Właściciel wymagał obecności internetu i GitHuba w planie. Plan doprecyzowany
w etap-4/INTERNET_WTYCZKI.md: odczyt, wyszukiwarka WWW, konektory/MCP, zapis.
Pierwszy kod: typowany rejestr odczytu, flagi wiadomości, planer do 2 narzędzi,
WWW HTTPS i publiczny GitHub. DNS/IP/TLS/redirecty/limity/proces/anulowanie,
źródła w historii, migracja 5 z kopią. Planer nie dostaje historii ani PDF.
Testy: 111 Python (107 OK, 4 Windows pominięte), 43 JS OK = 150 zaliczonych.
Próba realnego publicznego GitHuba: tool_dns_failed w środowisku QA — NIE zaliczono.
Prawdziwy Qwen3-8B z narzędziami/Windows/Job Object/wizualny UI do sprawdzenia.
Start Windows: git pull --ff-only, START.cmd, Ctrl+F5; bez nowych modeli/wheels.
Prywatny GitHub, zapis i pełna wyszukiwarka WWW nadal są planem.

## 02.11.2026 — większe strony i pierwszy moduł wyszukiwania 4b
Usunięto odrzucanie całego HTML po 512 KiB. Strumień/gzip/deflate, główna treść,
wyciąg 160000 znaków, lokalne notatki fragmentami, zachowany oryginał wycinka.
Dodano web_search Bing RSS i drugą rundę odczytu wyników, cache i budżety.
Testy: 123 Python (119 OK, 4 Windows pominięte), 43 JS OK = 162 zaliczonych.
Prawdziwa strona Wikipedii >1 MiB i 5 wyników RSS przetworzone przez urllib QA;
przypięty transport/natywny Qwen3-8B/nowy obieg Windows i UI nieodebrane.
Witryna zgłoszona przez właściciela zwróciła Site Unavailable, nie zaliczona.
Start: git pull --ff-only, START.cmd, Ctrl+F5. Nie ma nowego modelu ani migracji.
Plan i granice: etap-4/INTERNET_WTYCZKI.md, raport WEB_SEARCH_TESTY.txt.

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

## 03.11.2026 — zewnętrzny MCP i folder dokumentów
Opcjonalny oficjalny filesystem MCP 2.1.0 działa przez rzeczywisty Node/stdio.
Wybór folderu, przygotowanie pakietu, odłączenie i test w Połączeniach. Tylko
list_directory/read_text_file; .md/.txt do 32 KiB, 12000 znaków, katalog do 200
pozycji. Domyślna zgoda MCP nadal false. Brak uprawnień zapisu, dowolnego RPC,
komend modelu i nowych kont/tokenów. Zmiana root unieważnia stare źródła.
Node 24+ opcjonalny; npm ci z przypiętym lockiem, pustym npmrc, bez scripts.
Windows: 230 Python (229 OK, 1 symlink pominięty), Node 70/70. Rzeczywisty
oficjalny serwer: list/read, polskie nazwy, proces zagnieżdżony i API z sesją;
junction, wyjście ze ścieżki, zmiana folderu, brak runtime, brak CSRF, stare
źródło i zmieniony pakiet odrzucone. Chrome przez Playwright: wybór/test panelu
desktop i 390px z kontrolowanym API; nie jest to logowanie kontem właściciela.
Start START.cmd; brak migracji i obowiązkowych zależności. Kod mcp_files.py,
setup_mcp_filesystem.py, mcp-files.js. Kontrakt i raport docs/MCP_FOLDER.md oraz
MCP_FOLDER_TESTY.txt. Folder właściciela wymaga jawnego wyboru w panelu.
Dalej: drugi konkretny dostawca odczytowy MCP z kontraktem i testem, przed
ogólną konfiguracją serwerów; głos PL/EN nadal wymaga osobnego odbioru.

03.11.2026 — odbiór lokalnej aktualizacji powyższych pięciu paczek:
Wykonano kopię kodu i bazy, zachowano poświadczenia i istniejącą konfigurację.
Zainstalowane wszystkie zmiany od 60c504b, oficjalny runtime MCP przygotowany.
Rzeczywisty odczyt przez pakiet z folderu instalacji poprawny; folder właściciela
pozostawiono bez zmian (własny folder wymaga wyboru w Połączeniach).
Backend/model i zasoby UI działają; prywatna konfiguracja bez sesji zwraca 401.
START.ps1 -NoBrowser (ścieżka używana przez START.cmd): 3.609 s, PID modelu bez
zmiany. To ponowne otwarcie uruchomionej aplikacji, nie czas zimnego startu.
Rzeczywisty Qwen3-8B/CUDA wybrał mcp_files, odczytał memo.md przez zewnętrzny
serwer, zwrócił poprawny kod kontrolny i źródło; run completed, 65 znaków.
Sterownik po próbie: cała karta 6846/8192 MiB. Konto/kontroler tej rozmowy były
odizolowanymi fixture; inference i proces Node rzeczywiste. Bez hasła owner.
NIE URUCHOMIONO: nowe prywatne konto/PR z zapisem, pełna nowa instalacja,
mikrofon PL/EN i test wszystkich stron WWW. Nie są zaliczone przez te próby.

## 03.11.2026 — wybór dokumentów z folderu MCP
Połączenia → Przeglądaj dokumenty: katalog główny/podkatalogi/powrót,
oryginalne źródło i Zapytaj o dokument. Wybór dopisuje względną ścieżkę do
istniejącego szkicu, włącza MCP i przywraca fokus wiadomości; bez autosend.
Zdjęcie nie jest usuwane; przed takim wyborem trzeba je odłączyć. Zmiana root
i logout odrzucają stare wyniki/przyciski. Błąd nie udaje pustego katalogu.
Brak nowych narzędzi, zgód backendu, zależności i migracji; nadal tylko odczyt.
Windows: 231 Python (230 OK, 1 symlink pominięty), Node 74/74. Nowy test API
z rzeczywistym Node/MCP: główny katalog, docs i polski plik ze spacjami oraz
odczyt jego źródła. Chrome/Playwright: nawigacja, źródło i wybór, fokus szkicu,
MCP checked, desktop/390px; API tej próby UI kontrolowane, bez konta owner.
Nowej generacji na CUDA nie uruchamiano: zmiana dotyczy UI; przepływ MCP/CUDA
potwierdzony w poprzedniej paczce. Kod web/mcp-files.js/theme.css. Start
START.cmd i Ctrl+F5, wymagany wcześniej wybrany folder. Raport:
docs/MCP_PRZEGLADANIE_TESTY.txt. Dalej: drugi odczytowy dostawca MCP;
mikrofon PL/EN i nowe prywatne konto nadal wymagają osobnego odbioru.

03.11.2026: lokalną aktualizację przeglądania MCP zastosowano po kopii kodu
i bazy, z zachowaniem konfiguracji właściciela. Serwowane JS/CSS zgodne
z zainstalowanymi plikami; backend i model health=200, konfiguracja bez sesji
401. Odczyt przez zainstalowany Node/MCP poprawny. Ponowne START.ps1
-NoBrowser: 3.798 s, PID modelu bez zmiany; to otwarcie działającej
aplikacji. Bez nowej generacji AI, bez hasła owner i bez zmiany jego folderu.

## 03.11.2026 — wyszukiwanie nazw dokumentów MCP
mcp_files action=search/query: fragment nazwy z bieżącej prośby, rzeczywiste
search_files oficjalnego serwera i filtr casefold, do 20 wyników. Względne
wyniki autoryzują kolejny read; brak uprawnień zapisu i nowych zależności.
GET mcp-files/search i pole wyszukiwania w Połączeniach, źródło zachowuje query.
Rekurencja do 6 poziomów, 1000 pozycji i 64000 bajtów nazw absolutnych przed
uruchomieniem Node; duży zakres i nieukryte dowiązanie odrzucają całą operację.
Ukryte poddrzewa wyłączone; tylko .md/.txt do 32 KiB. Jawne matched_documents,
omitted_entries i truncated. To wyszukiwanie nazw, nie indeks treści.
Windows: 238 Python (237 OK, 1 symlink pominięty), Node 77/77. Rzeczywisty
search_files: podkatalog/polska nazwa/odczyt wyniku, ukryte pliki pominięte,
API z sesją i źródłem, stare root/obce query/glob/junction/limity odrzucone.
Chrome/Playwright desktop i 390px: wyszukiwanie, limit i wybór do szkicu;
API wizualnej próby kontrolowane, brak błędów konsoli. Nowej generacji CUDA
w tej paczce nie wykonywano. Start START.cmd; brak migracji. Kontrakt/raport:
docs/MCP_WYSZUKIWANIE.md i MCP_WYSZUKIWANIE_TESTY.txt. Następnie: odczyt
konkretnego zgłoszenia GitHub i dyskusji, nadal bez zapisu do serwisu.

## 03.11.2026 — zgłoszenia GitHub i komentarze
github_read section=issue/number: opis otwartego/zamkniętego zgłoszenia i do 10
komentarzy. Metadane przed/po odczycie porównane; bez obietnicy transakcyjnej
migawki komentarzy. Limity 4000 znaków opisu/1500 komentarza/8 etykiet, jawne
truncated/liczniki i comments_error. PR rozpoznany jako osobny typ; brak editable.
Lista issues filtruje PR z pierwszej porcji 21 wpisów i pokazuje do 10 zgłoszeń,
bez wnioskowania o całym repo z pustej/niepełnej porcji. Tylko GET.
Nowy PAT w kreatorze proponuje Issues: read; istniejący token niezmieniony,
prywatne Issues nieweryfikowane. Publiczny odczyt nadal bez konta.
Windows: 247 Python (246 OK, 1 symlink pominięty), Node 78/78. Rzeczywisty
ograniczony proces: python/cpython#161233, 1/1 komentarzy, bez ucięcia/zapisu.
Inference tej paczki kontrolowane; nowej generacji CUDA nie uruchamiano.
Kod app/github_issues.py/network/tools, UI błędów/kreatora. Start START.cmd,
brak deps/migracji. Kontrakt i raport docs/GITHUB_ZGLOSZENIA.md oraz plik TESTY.
Dalej: natywna weryfikacja indeksowania i wyszukiwania E5/RAG na CPU, PL/EN;
mikrofon i nowy zakres prywatnego konta nadal wymagają osobnego odbioru.

## 03.11.2026 — 2.5c: wznawialne dodawanie PNG/JPEG/PDF
Wysyłanie porcjami 512 KiB, SHA256, ponowny wybór tego samego pliku w tej samej
sesji wznawia potwierdzony offset. SQLite upload_sessions (migracja 007, kopia
przed zmianą), 3 aktywne wysyłki, TTL godzina, nadal 8 MiB/50 stron PDF i limit
200 MiB obejmujący bufory. Finalny załącznik i potwierdzenie atomowe, ponowienie
bez duplikatu. Logout czyści metadane przeglądarki; brak bajtów w sessionStorage.
Kompozytor i panel pokazują postęp. Wstrzymanie zachowuje porcje, jawny discard
robi kopię i zachowuje gotowe pliki. Generacja rekordu blokuje stary decoder
po usunięciu/odtworzeniu ID; sesja/Gaming/cancel ponownie sprawdzone przy zapisie.
Windows: 263 Python (262 OK, 1 symlink pominięty), Node 99/99. Rzeczywisty
SQLite, dekoder i kopia z kontrolą wyścigu zapisu. Chromium/Playwright z realnym
API i izolowaną bazą: 2252021 B PNG, kontrolowane zerwanie po 524288 B, reload
i wznowienie od 524288, gotowy plik raz, podgląd; discard pending1→0, gotowy1
zachowany, brak autosend. Mobile390 bez overflow. Konto/kontroler fixture;
produkcji/GPU nie używano w tej próbie. Awaria sieci była celowo wstrzyknięta.
Kod uploads.py/media/main, uploads.js/media/attachments. Start START.cmd;
kontrakt spec/etap-2.5c/UPLOAD.md, raport docs/UPLOAD_WZNOWIENIE_TESTY.txt.
Wizualne embeddingi pozostają planem. Dalej: zmiana nazwy rozmowy i eksport
Markdown/JSON ze źródłami; przygotowane osobno, jeszcze nie uznane za wdrożone.

03.11.2026: upload zainstalowany lokalnie po kopii programu/bazy. Rzeczywista
baza właściciela ma migrację 7 i upload_sessions, JS jest serwowany zgodnie
z plikiem instalacji, endpoint bez sesji zwraca401; backend/model health200.
Kod źródłowy/zainstalowany/uruchomiony zgodne (reuse_running exit0).
Nie logowano produkcyjnego konta do uploadu; pełny przepływ przeglądarkowy
został sprawdzony na izolowanym prawdziwym API opisanym w raporcie powyżej.

## 03.11.2026 — nazwa rozmowy i eksport Markdown/JSON
Menu Rozmowa w nagłówku: zmiana tytułu oraz pobranie wybranej rozmowy jako
Markdown/JSON v1. Całe teksty, metadane załączników i źródła W/D, bez binariów
i sekretów konfiguracji. 8 MiB/10000 wiadomości daje jawny błąd, bez ucięcia.
Eksport czyta snapshot bez blokady zapisu; rename sprawdza właściciela/CSRF,
zachowuje wiadomości, źródła, szkic i aktywną generację. Brak migracji/deps.
UI epoki blokują stare wyniki po zmianie rozmowy/logout. Nowa rozmowa z odpowiedzi
starej sesji nie odtwarza widoku. Test_cutoff odizolowany od flag shutdown innego
fixture TestClient; nie zmieniono przez to zachowania produkcyjnej inferencji.
Windows: 282 Python (281 OK, 1 symlink pominięty), Node 107/107. Rzeczywisty
SQLite/HTTP i Chromium: polski tytuł, PATCH1, pełne pobrania 16404 znaków+W1,
szkic zachowany, messages POST0; mobile390, Escape/fokus/logout poprawne.
Konto/kontroler fixture, produkcja/GPU nietknięte w QA; brak nowej generacji AI.
Kod conversation_export.py/conversations.py/main i conversation-actions.js.
Start START.cmd, Ctrl+F5. Kontrakt docs/ROZMOWY_NAZWA_EKSPORT.md, raport
ROZMOWY_EKSPORT_TESTY.txt. Następnie: wyszukiwanie w treści własnej historii
z otwieraniem konkretnej starszej wiadomości, bez modelu i usług zewnętrznych.

## 03.11.2026 — wyszukiwanie treści historii i dokładny punkt wiadomości
Panel historii: jawne wyszukiwanie literalnej treści własnych wiadomości,
Unicode casefold, fragmenty240 znaków. Do2000 sprawdzonych/20trafień na porcję,
kursor do starszych bez pomijania rekordów, także przy pustej porcji. Snapshot
readonly bez rezerwacji zapisu, owner ACL przed LIMIT; bez modeli/indeksu/deps.
Kliknięcie otwiera dokładne seq przez messages?at=, wyróżnia punkt; Najnowsze
wraca do końca. Szkic zachowany, generowanie blokuje zmianę widoku. Wyszukiwanie
nie zamyka mobilnego sidebar, wybór wyniku zamyka go jawnie. Headerstarszych
stron zawija kontrolki na telefonie zamiast wychodzić poza ekran.
Windows:291 Python (290 OK,1 symlink pominięty), Node120/120. Rzeczywisty SQLite
i HTTP: ACL, kursory, Unicode, braki trafień z next, dokładny starypunkt.
Chromium/Playwright z realnym API i130wiadomościami: seq61 poza latest50,
wyróżnienie/powrót, 2porcje wyników, mobile390/fokus/logout/late response,
szkic zachowany, messages POST0 i model0. Konto/kontroler fixture; GPU bez użycia.
Brak migracji. Kod conversation_search.py, conversation-search.js, sidebar/app.
Start START.cmd i Ctrl+F5. Kontrakt docs/WYSZUKIWANIE_HISTORII.md i plik TESTY.
Dalej: nowa rozmowa od wybranej odpowiedzi, bez naruszania oryginału i bez
automatycznej generacji; przygotowywana osobno przez agentów.

## 03.11.2026 — nowa rozmowa od wybranej odpowiedzi
Przycisk pod zapisaną odpowiedzią tworzy osobną rozmowę z prefiksem do tej
odpowiedzi włącznie. Nowe ID, zachowane role/teksty/daty/W/D/obrazy, oryginał
bez zmian. Własne pliki współdzielone referencjami, nie snapshot binariów;
ich usunięcie/zmiana dotyczy obu rozmów. Bieżąca sesja obrazu zamiast dawnej.
Bez kopiowania runs/zezwoleń i bez generacji/wysyłania wiadomości. Zachowany
tekst szkicu; niewysłany obraz czyszczony przy zmianie rozmowy jak dotychczas.
SQLite kopiuje atomowo z potwierdzeniem idempotencji24h. Równoległe ponowienia
i utrata odpowiedzi nie duplikują operacji w tym zakresie. Owner/session/CSRF,
tylko assistant, blokada aktywnej generacji źródła, limity1000/8MiBUTF8 tekstu
bez cichego skrócenia. Błąd GET po201 ma prawdziwy komunikat, pusty bezpieczny
widok, odświeżoną listę i Najnowsze do ponowienia odczytu bez kolejnej kopii.
Windows:302 Python (301 OK,1 pominięty symlink), Node134/134. Realny Chromium,
HTTP i SQLite: zgubiony201/retry ten sam ID, prefix2/original4/W1/freshIDs,
szkic, mobile390, brak messagesPOST/model; awaria otwarcia i odzysk odczytu.
Konto/kontroler fixture, brak nowej inferencji GPU; głos nie sprawdzany tutaj.
Start START.cmd i Ctrl+F5. Brak migracji/deps. Kod conversation_branch.py,
conversation-branch.js i app/main. Kontrakt docs/ROZMOWY_GALEZIE.md, raport TESTY.
Następnie: kopiowanie pełnych wiadomości jednym przyciskiem z obsługą błędów
schowka, bez uruchamiania modelu i bez zmiany historii.

## 03.11.2026 — kopiowanie całych wiadomości
Przycisk pod user/assistant kopiuje pełny oryginalny tekst z Markdown/Unicode
i oznaczeniami źródeł, także bieżący fragment streamingu. Bez HTML, obrazów
ani dodatkowych wycinków źródeł. Jawny klik, brak network/model/autosend.
Schowek denied/unsupported/pusty tekst mają uczciwy komunikat. Pending blokuje
ponowienia bez odbierania fokusu; logout/full-load unieważniają stare wyniki.
Już zleconego zapisu systemowego nie cofamy; OS schowek nie jest czyszczony.
Szkic pozostaje bez zmian. Kod message-copy.js i bubble/load/showLogin.
Windows:302 Python (301 OK,1 pominięty), Node145/145. Realny Chromium z lokalnym
schowkiem: user/assistant, długi UnicodeMarkdown, błędy i późny wynik/logout,
mobile390. Konto/kontroler fixture, messagesPOST0/model0; brak nowej inferencji.
Brak migracji/deps. START.cmd i Ctrl+F5. Kontrakt docs/KOPIOWANIE_WIADOMOSCI.md
i dosłowny raport TESTY. Dalsze etapy: pamięć wizualna2.5c i pozostałe integracje
według planu; nie uznajemy tych zakresów za ukończone przez funkcje historii.

Potwierdzenie poprzedniej paczki gałęzi07a409e: lokalna aktualizacja po kopii
kodu/bazy; backend/model200, oficjalny MCP read prawdziwym procesem z folderu
testowego, START3.892s bez zmiany PID modelu. Odciski źródeł/zainstalowanego/
uruchomionego kodu zgodne przed rozpoczęciem zmian kopiowania. Bez logowania
produkcyjnego konta i bez zmiany jego folderu MCP.

03.11.2026: paczka kopiowania8699f16 zainstalowana lokalnie po kopii kodu/bazy.
Odciski źródła/instalacji/uruchomionego backendu identyczne; cztery pliki JS/CSS
serwowane dokładnie, health200, branch bez logowania401. Model gotowy według
API; brak nowej inferencji i brak testu produkcyjnego konta. Izolowany serwer
przeglądarkowych testów zatrzymany; produkcyjny backend pozostaje uruchomiony.

## 03.11.2026 — historia commitów i odczyt konkretnego SHA GitHuba
github_read section=commits: pierwsza porcja do10 z opcjonalnym ref. section=commit:
pełny SHA40/64, weryfikacja zgodności, opis4000/statystyki/rodzice, do20plików,
patch6000, razem130000 znaków. Jawne brakujące/binarne/pominięte patche, filtry
poświadczeń dla obu nazw po rename, total_files=null zamiast wymyślonej całości.
Źródła kanoniczne. Bez editable, uprawnień do draft i nowych metod zapisu.
Planer oznacza przycięcie tekstu800 i nie dubluje listy przez items w kontekście.
Publiczne bez konta, prywatne istniejące DPAPI/allowlist/Contentsread; prywatne
konto nowego zakresu NIE PRZETESTOWANE. Brak migracji, zależności i zmiany GPU.
Windows:314 Python (313 OK,1 symlink pominięty), Node146/146. Realny worker GET
odczytał10commitów i3patche wybranego SHA bez konta. Rzeczywisty llama-serverCUDA
wybrał narzędzie i zakończył odpowiedź395znaków z zapisanym właściwym źródłem;
konto/kontroler fixture, model prawdziwy. VRAM po odpowiedzi7119/8192MiB,
pojedynczy pomiar. Bez zewnętrznych zapisów. Testy UI komunikatów w Node;
nowej próby przeglądarkowej tego zakresu nie wykonywano.
Start START.cmd, Ctrl+F5. Kontrakt docs/GITHUB_COMMITY.md i raport TESTY.
Dalej: kolejne konkretne integracje odczytowe według planu4c; pamięć wizualna
2.5c pozostaje osobnym niezrealizowanym zakresem. Historia rozmów nie zalicza
głosu, nowego prywatnego konta ani pozostałych etapów.

03.11.2026: paczka commitów9ab600c zainstalowana lokalnie po kopii kodu/bazy.
Odciski źródeł/instalacji/uruchomionego backendu zgodne, tools.js serwowany
dokładnie, nowe sekcje zaakceptowane przez zainstalowany schemat. Health200,
historia bez sesji401, rzeczywisty model gotowy. Nie logowano konta właściciela.

## 03.11.2026 — 4c: adapter publicznych kanałów RSS/Atom
Wspólny rejestr: feeds/feed_read, zgoda istniejącego Internetu. RSS2/Atom1UTF8,
do5wpisów, opisy300, kolejność wydawcy bez obietnicy całego archiwum/artykulów.
Panel testu faktycznie czyta kanał; dopisuje pytanie do szkicu bez autosend,
bez przechowywania URL i bez usuwania zdjęcia. XMLbase/alternate, ograniczenia
XML20/5000/512KiB; DTD/encje, lokalne linki, zły format/kodowanie odrzucone.
Artykuł dostępny web_read dopiero z rzeczywistych wyników; brak nowych zgód.
Test sesja/CSRF+recheck; logout i zmiana URL blokują późne odpowiedzi.
Windows326 Python (325 OK,1 symlink pominięty), Node154/154. Prawdziwe procesy
odczytały RSS Django i Atom CPython po5/10. Chromium/realAPI: list5, szkic/fokus,
mobile390, messagesPOST0/model0; faultXML i held200 po logout zignorowane.
Osobno realny CUDA wybrał feed_read i zakończył odpowiedź345znaków ze źródłem;
konto/kontroler fixture. VRAM6968/8192MiB, pojedynczy pomiar. Brak nowego testu
głosu/prywatnych kont. Poprawiony stary test budżetu planera, bez zmiany GPU.
Brak migracji/deps. START.cmd/Ctrl+F5. Kontrakt docs/RSS_ATOM.md, raport TESTY.
To adapter RSS, nie drugi dostawca MCP. Etap4c nadal częściowo wdrożony;
dalej: uporządkowanie panelu Połączenia, kolejny dostawca MCP, pamięć wizualna2.5c.

## 03.11.2026 — zwijane sekcje i stan integracji
Panel Połączenia: cztery natywne details/summary, stała kolejność GitHub/MCPdocs/
MCPfolder/RSS, widoczny krótki stan bez rozwijania formularzy. Bez auto-testów
i nowych żądań przy zwijaniu. Błąd lokalnej konfiguracji GitHuba nie udaje
publicznego połączenia; można jawnie odłączyć lokalnie z istniejącą kopią.
Logout zwija i resetuje stany, stare żądania nie nadpisują nowej sesji/pola
tokenu ani blokady przycisków. Nieudany test folderu MCP zachowuje błąd.
Windows326 Python (325 OK,1 symlink pominięty), Node164/164. Realny Chromium/
API: cztery zamknięte grupy, Enter, mobile390 bez overflow/okno484px, tokeninput
czyszczony przy close, logout reset; rzeczywisty odczyt MCPdocs OK, wymuszony
błąd widoczny. FoldingPOST0/messages0/model0. Inference tej paczki nieuruchamiana.
Kod integration-groups.js i moduły UI, bez migracji/deps. START.cmd/Ctrl+F5.
Kontrakt docs/POLACZENIA_SEKCJE.md i raport TESTY. Etap4c nadal częściowy.
Dalej: konkretny drugi dostawca MCP tylko do odczytu, następnie pamięć wizualna2.5c.

Potwierdzenie poprzedniej paczki RSSdb66f4b: lokalna instalacja po kopii kodu/
bazy, odciski źródło/instalacja/backend zgodne. Zainstalowany realny worker
odczytał5wpisówDjango; plikiJS zgodne, backend200, endpointRSS bez sesji401.
Nie używano produkcyjnego konta. Weryfikacja wykonana przed zmianami panelu.

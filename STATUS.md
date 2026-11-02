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

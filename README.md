# KripAI

Lokalny asystent AI na Windows 11: rozmowy, zdjęcia, PDF i głos w panelu
przeglądarki. Backend działa bezpośrednio na komputerze, dane zapisuje SQLite,
a modele uruchamia `llama-server.exe` z CUDA. Bez WSL, Dockera i Caddy.

**Status: wersja rozwojowa.** Poniższe funkcje mają implementację i testy,
ale pełny odbiór instalacji, CUDA, VRAM oraz głosu na docelowym Windows
pozostaje niewykonany. Nie jest to deklaracja gotowości produkcyjnej.

## Szybki start

**Gdzie: Windows 11, Eksplorator plików.**

1. Rozpakuj cały projekt do osobnego folderu. Nie przenoś samego START.cmd.
2. Kliknij **START.cmd**. Przygotuje prywatny Python, biblioteki i modele;
   przy pierwszej instalacji poprosi o ustawienie własnego hasła.
3. Otwórz **http://localhost:8765**. Login: **owner**, hasło: ustawione przez Ciebie.
4. Po aktualizacji odśwież panel przez **Ctrl+F5**.
5. Zakończ program przez **WYLACZ.cmd**. Zamknięcie karty nie wyłącza modeli.

Potrzebujesz Windows 11 x64, sterownika NVIDIA i miejsca na modele. Docelowy
komputer: RTX 3060 Ti 8 GB i 32 GB RAM. Zalecany zapas wolnego miejsca: co
najmniej 16 GB przed pierwszym przygotowaniem. Model tekstowy to około 5 GB,
model obrazu z projektorem około 3,34 GB, model głosu około 488 MB; dochodzą
binaria i biblioteki. Pobieranie wymaga internetu, lokalne wnioskowanie nie
korzysta z chmurowego API. Nie trzeba konta dostawcy modelu.

START może uruchomić oficjalny instalator Microsoft Visual C++, jeżeli system
nie ma wymaganego runtime. Nie jest instalowany globalny CUDA Toolkit ani Python.

## Zaimplementowane

- [x] Logowanie właściciela, hasło bez wartości domyślnej, sesje i wylogowanie.
- [x] Rozmowy i trwała historia SQLite; stronicowanie starszych wiadomości.
- [x] Strumieniowanie odpowiedzi SSE, anulowanie i ochrona przed podwójnym wysłaniem.
- [x] Budżet kontekstu liczony tokenizerem; starsze tury pozostają w historii.
- [x] Tryb Gaming: kliknięcie zatrzymuje własny proces modelu, powrót go uruchamia.
- [x] Zdjęcie przez **Ctrl+V**, przeciągnięcie lub „＋ Zdjęcie”, miniatura przed wysłaniem.
- [x] Jedno PNG/JPEG razem z pytaniem; odpowiedź VLM i obraz w historii rozmowy.
- [x] Panel PNG/JPEG/PDF: podgląd, wybór strony, warstwa tekstowa, OCR i pytania o obraz.
- [x] Automatyczne przełączanie modelu tekstowego i VLM bez ich równoległego uruchamiania.
- [x] Markdown: nagłówki, listy, cytaty, tabele, pogrubienie i bloki kodu z kopiowaniem.
- [x] Lokalne kolorowanie oznaczonych bloków JS/TS, Python, HTML, CSS, JSON, SQL, shell i PowerShell.
- [x] Internet: wyszukiwanie WWW, odczyt wyników i większych stron; publiczny GitHub.
- [x] Pamięć tekstowych PDF: indeksowanie, wybór dokumentów, źródła ze stroną i wycinkiem.
- [x] Podstawowe wzory matematyczne jako MathML; nieznany zapis pozostaje tekstem.
- [x] Nagrywanie do 30 sekund, lokalna transkrypcja Whisper do pola korekty.
- [x] Odczyt tekstu lokalnym System.Speech, PL/EN zależnie od zainstalowanych głosów.
- [x] Kopie i przywracanie bazy wraz z plikami, reset hasła, odinstalowanie.
- [x] Migracje SQLite z kopią przed aktualizacją istniejącego schematu.
- [x] Opcjonalny import historii przez API starego lokalnego panelu.
- [x] Limit odpowiedzi 2048 tokenów, ostrzeżenie o ucięciu i przycisk „Kontynuuj”.

## Do zrobienia i plan etapów

| Etap | Stan | Zakres |
| --- | --- | --- |
| 1 — rdzeń Windows | Implementacja, odbiór natywny nieukończony | Instalator, chat, SQLite, procesy modeli, Gaming i odzyskiwanie danych |
| 2 — głos | Profil próbny, jakość do pomiaru | STT/TTS PL/EN, mikrofon, opóźnienia i stabilność na docelowym PC |
| 2.5a — obrazy i PDF | Implementacja, odbiór GPU/UI nieukończony | Wklejanie zdjęć, OCR, VLM i podgląd dokumentów |
| 2.5b — RAG | Pierwszy zakres zaimplementowany, odbiór Windows nieukończony | Tekstowe PDF, E5 CPU, sqlite-vec, checkpointy i źródła w czacie |
| 2.5c — większe pliki | Niezaimplementowany | Wznawianie uploadów i wizualne embeddingi |
| 3 — Cardputer | Niezaimplementowany | Osobna zabezpieczona bramka, parowanie i unieważnianie urządzeń |
| 4 — internet i integracje | Odczyt 4a i pierwszy moduł wyszukiwania 4b, odbiór Windows nieukończony | WWW/GitHub, dalej inni dostawcy, konektory/MCP, prywatne konta i zapis |
| 5 — zadania w tle | Niezaimplementowany | Trwały worker, harmonogram, powiadomienia i koordynacja GPU |
| 6 — Android | Niezaimplementowany | Aplikacja mobilna, synchronizacja i bezpieczna bramka |

Pozostałe ograniczenia wymagające dalszej pracy:

- [ ] Pełny test Windows: czysta instalacja, Job Object, CUDA, VRAM, restart i uninstall.
- [ ] Ręczny test wyglądu i obsługi przeglądarki, mikrofonu oraz głosów PL/EN.
- [ ] Pomiar jakości polskiego STT i OCR na rzeczywistych nagraniach/zdjęciach.
- [ ] Pełna pamięć multimodalna: kolejne pytanie bez załącznika nie analizuje dawnych pikseli.
- [ ] Wiele zdjęć w jednej wiadomości i analiza całego dokumentu zamiast pojedynczej strony.
- [ ] Pełny LaTeX oraz dokładniejsze wznawianie długiego kodu.
- [ ] Automatyczne streszczanie rozmów, pamięć poza wybranymi PDF oraz OCR skanów do RAG.

Szczegółowe kryteria odbioru: [plan etapów](spec/06-rollout.md).

## Modele i limity

| Element | Aktualne ustawienie |
| --- | --- |
| Tekst | Qwen3-8B Q4_K_M, llama.cpp b12000 |
| Obrazy | Qwen3-VL-4B-Instruct Q4_K_M + projektor F16 na CPU |
| STT | Whisper.cpp b5454, small wielojęzyczny, CPU |
| TTS | System.Speech i lokalne głosy Windows |
| Kontekst / odpowiedź | 4096 / maks. 2048 tokenów |
| Obraz w wiadomości | Jedno PNG/JPEG do 8 MiB |
| PDF | Do 50 stron, wybrana strona analizowana osobno |
| Magazyn plików | Do 50 plików i 200 MiB oryginałów z podglądami |
| Podgląd obrazu | Do 1024 px; mały tekst może wymagać wycinka |

Przypięte rewizje i sumy SHA-256 są w manifestach `scripts/*-lock.json`.
Koniec budżetu nie oznacza pełnej odpowiedzi: panel pokazuje ostrzeżenie.
„Kontynuuj” przygotowuje nową wiadomość z końcówką poprzedniej, do sprawdzenia
przed wysłaniem. Nie gwarantuje idealnego połączenia fragmentów kodu.

## Dane i obsługa

| Położenie / przycisk | Znaczenie |
| --- | --- |
| `%LOCALAPPDATA%\KripAI` | Zainstalowany program i prywatny runtime |
| `%LOCALAPPDATA%\KripAI-data` | Baza, rozmowy, pliki, modele i klucz lokalnego LLM |
| `%LOCALAPPDATA%\KripAI-backups` | Lokalne kopie, zachowywanych 14 ostatnich |
| `BACKUP.cmd` | Tworzy kopię SQLite z rozmowami i załącznikami |
| `PRZYWROC_KOPIE.cmd` | Przywraca cały stan, z kopią bieżącego stanu przed operacją |
| `RESET_HASLA.cmd` | Zmienia hasło i unieważnia sesje |
| `ODINSTALUJ.cmd` | Usuwa program; dane domyślnie zostają |
| `IMPORT_HISTORII.cmd` | Importuje historię z działającego starego panelu |

**Przyciski uruchamiaj w Windows.** Kopie są lokalne — przenieś ważną kopię na
inny dysk. Usunięty plik może pozostać w starszych kopiach; to nie bezpieczne
wymazanie nośnika. Anulowany upload może wymagać usunięcia pliku w panelu.

## Testy i stopień weryfikacji

Ostatni pełny przebieg: **123 testy Python — 119 OK, 4 pominięte Windows;
43 testy JavaScript OK. Razem 162 zaliczonych i 4 pominięte.**

SQLite, dekodery, HTTP/SSE i procesy potomne są rzeczywiste. Inference w testach
regresji zastępują kontrolowane atrapy. Testy UI używają modelu DOM, nie testują
wyglądu przeglądarki. Bieżące Linux QA: Python 3.12.14, SQLite 3.53.1, Pydantic 2.14.1,
Pillow 12.3.0 i pypdfium2 5.14.0;
paczka Windows zawiera Pillow 13.0.0, którego natywnego wykonania nie potwierdzono.

**NIE URUCHOMIONO w QA:** pełna instalacja i odinstalowanie Windows, CUDA/VRAM,
natywny Job Object, mikrofon i wizualny odbiór UI. To pozostają zadania odbioru.

- **Windows:** uruchom `TESTY.cmd` — sprawdź dokładnie raport i testy pominięte.
- **Windows / PowerShell, opcjonalnie dla testów JS:** mając Node.js, w katalogu projektu
  uruchom `node --test tests/test_*ui.cjs`. Node nie jest potrzebny do działania KripAI.
- Dosłowne wyniki: [raport testów](docs/WYNIKI_TESTOW.txt).
- Ręczne kroki i oczekiwane wyniki: [pełna instrukcja](docs/INSTRUKCJA.md).

## Bezpieczeństwo i zawartość repo

Backend nasłuchuje lokalnie na 127.0.0.1. Sesja, Origin, CSRF i Host chronią API.
**Nie wystawiaj tego HTTP przez tunel ani LAN.** Dostęp zdalny jest osobnym,
niezaimplementowanym etapem. Tekst z obrazów, plików i odpowiedzi modelu jest
niezaufany: nie nadaje uprawnień, nie zatwierdza działań i nie wykonuje kodu.
Dekoder ma limit pamięci/czasu; Windows Job Object nie jest pełnym sandboxem.

Repo obejmuje kod, testy, dokumentację i manifesty zależności instalatora.
Binarne `vendor/` jest wykluczone z Gita. START pobiera brakujący prywatny Python
z python.org, a koła z PyPI (dokładna nazwa i SHA-256 z locka, bez wyboru latest).
Pełna paczka ZIP nadal zawiera `vendor/`; sprawne lokalne pliki nie wymagają
ponownego pobierania bibliotek. Nowa ścieżka START z samego repo wymaga testu Windows.
Nie dodawaj `.env`, kluczy, bazy, rozmów, zdjęć, nagrań, kopii, runtime ani modeli.
Duże modele są pobierane przez START, nie przechowywane w Git.
Licencje komponentów: [THIRD_PARTY.md](docs/THIRD_PARTY.md).
Licencja własnego kodu projektu nie została jeszcze wybrana; obecność na GitHubie
sama nie nadaje mu licencji open source.

## Struktura projektu

- `app/` — backend, SQLite, autoryzacja, historia, modele, media i głos.
- `web/` — interfejs przeglądarkowy i lokalne formatowanie.
- `scripts/` — instalator, zarządzanie, pobieranie i manifesty wersji/SHA.
- `tests/` — zachowania, awarie, izolacja użytkowników i regresje UI.
- `vendor/` — prywatny Python i wheels z licencjami, w ZIP lub pobierane, poza Gitem.
- `spec/` — decyzje i plan etapów; źródło prawdy: [INDEX.md](spec/INDEX.md).
- `docs/` — instrukcja, źródła i wyniki testów.
- [STATUS.md](STATUS.md) — historia wykonanych modułów i techniczny dług.

Bieżący stan i dalsze kroki: [PROJECT_STATE.md](PROJECT_STATE.md).
Audyt odzyskania: [docs/AUDYT_2026-11-02.md](docs/AUDYT_2026-11-02.md).

## Pamięć dokumentów — etap 2.5b

Po aktualizacji uruchom START.cmd (dodatkowy model około 126 MiB) i Ctrl+F5.
Dodaj PDF przez „Zdjęcia i PDF”, otwórz „Pamięć dokumentów”, kliknij Indeksuj
i zaznacz gotowy dokument. Zadaj pytanie w czacie — pod odpowiedzią pojawią się
nazwy, strony i użyte fragmenty. Do 5 wybranych PDF; wybór można wyczyścić.
Pauza/wznowienie zapisuje postęp po stronie. Usuń indeks zachowuje PDF.

Na razie PDF musi mieć tekst na każdej stronie (do 12000 znaków/stronę).
Skany, PNG/JPEG i inne formaty nie są automatycznie indeksowane. Jednoczesne
zdjęcie i dokumenty wyślij osobno. Podczas indeksowania pytanie RAG może wymagać
poczekania; zwykły czat działa dalej. Encoder E5 pracuje na CPU; narzut RAM/VRAM
oraz nowa DLL wymagają testu Windows. Szczegóły: [RAG.md](spec/etap-2.5b/RAG.md).

Próba rzeczywistego E5 i sqlite-vec na Linux przeszła; trzy przykłady PL/EN
nie są pełnym benchmarkiem ani testem poprawności odpowiedzi modelu tekstowego.

## Internet i GitHub — odczyt i wyszukiwanie

Po aktualizacji START.cmd i Ctrl+F5. Włącz „Internet: szukaj i czytaj” i zadaj
pytanie bez linku albo wklej URL do streszczenia. Wyszukiwanie używa publicznego
Bing RSS bez klucza API; model może odczytać link z wyników. Obecnie do 2 rund,
4 wywołań i jednego wyszukiwania na pytanie. Zapytanie trafia do wyszukiwarki;
planer nie dostaje prywatnej historii ani PDF. Domyślnie internet jest wyłączony.

Duża strona nie jest już odrzucana tylko za przekroczenie 512 KiB. Odczyt jest
strumieniowy, obsługuje gzip/deflate i główną treść HTML. Długi tekst model
przetwarza lokalnie fragmentami. Przy granicy zasobów wykorzystuje dostępny
fragment i oznacza zakres. Źródła pokazują oryginalny wycinek, nie notatki modelu.
Większa strona może wymagać więcej czasu. Limit pamięci GPU pozostaje bez zmian.

„Publiczny GitHub”: np. „Przeczytaj README kripusek/kripai”. Prywatne repo i zapis
są kolejnymi etapami. Wtyczki/tokeny ChatGPT nie przenoszą się do KripAI.
Logowanie, CAPTCHA, JavaScript i blokady serwisów nadal mogą uniemożliwić odczyt;
nie obiecujemy obsługi wszystkich witryn. Plan i granice: [integracje](spec/etap-4/INTERNET_WTYCZKI.md).

QA przetworzyło rzeczywistą stronę >1 MiB i kanał RSS przez trasę urllib hosta;
transport Windows i rzeczywisty Qwen3-8B z nowym obiegiem wymagają odbioru.
Strona ze zgłoszenia zwracała tutaj Site Unavailable. Raport: [WEB_SEARCH_TESTY.txt](docs/WEB_SEARCH_TESTY.txt).

Integracje 4c: panel stanu przy przełącznikach internetu, odczyt plików i katalogów GitHuba, opcjonalny prywatny dostęp DPAPI. Konfiguracja i granice: [docs/INTEGRACJE_4C.md](docs/INTEGRACJE_4C.md).

Nowe: automatyczna kontynuacja długich odpowiedzi tekstowych (do 8 porcji),
zachowanie częściowego tekstu przy awarii oraz lokalne propozycje zmian GitHuba
z publikacją na nowej gałęzi i PR w ograniczonym repo. [Konfiguracja i limity](docs/PR_I_DLUGIE_ODPOWIEDZI.md).

Opcje rozmowy są teraz pod przyciskiem +. GitHub połączysz w oknie Połączenia,
bez PowerShella: [kreator i zasady](docs/MENU_I_POLACZENIE_GITHUB.md).

Kopie obejmują również propozycje i dziennik GitHuba. Przenoś cały zestaw
SQLite + .github + .github.sha256: [zasady i odzysk](docs/KOPIE_DZIENNIKA_GITHUB.md).

Nowe MCP: w menu + wybierz „MCP: dokumentacja KripAI”, a następnie poproś np.
o odczyt docs/KOPIE_DZIENNIKA_GITHUB.md. Połączenia zawierają rzeczywisty test
serwera. Działa lokalnie bez konta, wyłącznie do odczytu dokumentacji programu:
[użycie, wyniki i granice MCP](docs/MCP.md). Zewnętrzne serwery MCP są dalszym etapem.

Wyszukiwanie dokumentacji modułów Pythona korzysta również z oficjalnego indeksu;
[zasady i wyniki](docs/DOKUMENTACJA_PYTHONA.md).

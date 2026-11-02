# KripAI — stan projektu
Aktualizacja: 02.11.2026. Ten plik opisuje bieżącą paczkę; STATUS.md zachowuje historię.

## Aktualny etap
Etapy 1, 2 i 2.5a mają implementacje. Odbiór natywnego Windows nieukończony.
Etap 2.5b ma pierwszy działający zakres: tekstowy PDF → indeks E5/sqlite-vec
→ wybór dokumentów → pytanie w czacie → źródła ze stroną i wycinkiem.
Dokumenty skanowane i inne formaty nie są jeszcze indeksowane. Rozpoczęty moduł 4a: jawny odczyt WWW/publicznego GitHuba. Rozpoczęto też 4b: wyszukiwanie WWW i większe strony. Etapy 2.5c, 3, 4c–4d i 5–6 planem.

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

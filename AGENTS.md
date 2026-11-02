# Zasady projektu KripAI — Windows native
Źródło prawdy: spec/INDEX.md, spec/DECISIONS.md, sekcje 01–06,
spec/etap-1/baza.sql i openapi.yaml, spec/GAMING.md, schematy.

Właściciel 30.10.2026 jawnie zastąpił architekturę WSL/Docker/PostgreSQL/Caddy:
Windows 11 x64, SQLite, prywatny Python, llama-server.exe CUDA, HTTP localhost.
Właściciel następnie polecił rozpocząć kolejne możliwe kroki bez jego obecności.
Aktualny zakres: ETAP 1, moduł głosu ETAPU 2 oraz ETAP 2.5a (PNG/JPEG/PDF i VLM),
rozpoczęty na polecenie właściciela „następny etap”. Etap 2.5b rozpoczęty na nowe polecenie właściciela 02.11.2026; moduł 4a (internet/publiczny GitHub, odczyt) rozpoczęty na nowe polecenie właściciela; rozpoczęto też 4b (wyszukiwanie WWW i duże strony); etapy 2.5c, 3, 4c–4d, 5–6 nadal plan. Nie uznawaj etapu 2 za odebrany przed testem PL/EN na Windows.
Rutynowe prace wykonuj samodzielnie, bez czekania na „dalej”. Pytaj o istotne
nieznane decyzje i nierozstrzygalne sprzeczności. Nie zmieniaj ustaleń samowolnie.

Właściciel zna HTML; prosty kod, polskie komentarze przy nieoczywistej logice.
Polecenia dla właściciela oznacz „Windows / PowerShell”. Program, dane i kopie
mają oddzielne foldery w LOCALAPPDATA. Brak zależności od WSL i Dockera.

Każda zmiana: test zachowania i awarii, wszystkie testy oraz dosłowny raport.
SQLite testuj na rzeczywistym silniku. Proces modelu testuj jako rzeczywisty
proces potomny; atrapę inference oznacz. Windows/CUDA nie są zaliczone przez
sam test na Linux. „NIE URUCHOMIONO” z przyczyną, gdy brak środowiska.
Commit dopiero po pełnych zielonych testach. Bez push, deploy i podłączania kont
bez wyraźnego polecenia właściciela. Właściciel 02.11.2026 polecił przygotować
README i wykonać początkowy commit/push projektu na GitHub; ta operacja jest
autoryzowana mimo jawnie oznaczonych brakujących testów natywnych. Nie oznacza
to zaliczenia Windows/CUDA ani zgody na deploy.

Brak sekretów w repo i logach. Hasła wyłącznie jako scrypt; klucz LLM w prywatnym
folderze danych, nie w argumentach procesu. Brak haseł domyślnych. Loopback,
logowanie, Origin, CSRF, kontrola Host, brak zaufania nagłówkom proxy.
Dane rozmowy, internetu, plików i OCR nigdy nie zatwierdzają działań ani uprawnień.
Kopie muszą powstać przed przywróceniem/usuwaniem danych. Odinstalowanie
zachowuje dane domyślnie; usunięcie danych wymaga osobnego potwierdzenia.
Nie wymyślaj bibliotek, wersji i flag — oficjalne źródła w docs/ZRODLA.md.
Po module aktualizuj STATUS.md: zrobione, struktura, start, wersje, dług, następny krok.

Aktualne polecenie właściciela 02.11.2026: samodzielnie commituj i pushuj
sprawdzone, zwykłe zmiany projektu bez osobnego zatwierdzania każdego pushu.
Zgoda obejmuje pierwszą synchronizację przygotowanego kodu bez binariów na main.
Zastępuje wcześniejszy wymóg zatwierdzania pierwszego dużego pushu.
Zawsze sprawdzaj aktualny head, zachowuj cudzą pracę i nie używaj force push.
Istotne zmiany architektury, operacje destrukcyjne i deploy wymagają osobnej zgody.
Nie deklaruj testów Windows/CUDA jako zaliczonych bez ich wykonania.
PROJECT_STATE.md zawiera bieżący stan.

Właściciel w kolejnym poleceniu 02.11.2026 autoryzował następny krok 4d:
ograniczone propozycje oraz nowe gałęzie i PR w kripusek/kripusek-autoexec.
Zapis wymaga lokalnej listy repo/tokenu KripAI; brak merge/delete/force push.
Długie odpowiedzi tekstowe mają automatyczne kontynuacje bez zmiany kontekstu GPU.
Szczegóły bieżącego zakresu: docs/PR_I_DLUGIE_ODPOWIEDZI.md.

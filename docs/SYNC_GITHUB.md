# Zakres pierwszej synchronizacji — zatwierdzony przez właściciela
Cel: publiczne repo https://github.com/kripusek/kripai, gałąź main.
Odczytana baza: 65667aab5d5da25fbdf77b2f947786f560801a8e, tylko README.md.
Przed wykonaniem ponownie sprawdzić head; nową pracę porównać i scalić, bez force push.

Do wysłania: źródła aplikacji, skrypty Windows, interfejs, testy, specyfikacja,
licencje komponentów, manifesty SHA, PROJECT_STATE i raport odzyskania.
README zachowuje istniejącą treść projektu i uzupełnia faktyczne nowe funkcje,
wyniki QA oraz sposób przygotowania zależności. Nie usuwa się istniejącej pracy.

Nowa implementacja względem ZIP: web/syntax.js i integracja w format.js/index/CSS,
4 testy JS, bootstrap brakujących zależności w downloads.py/start.ps1, 5 testów
Python, .gitignore oraz aktualizacja dokumentacji. Nie ma migracji bazy.

Wykluczone: binarne vendor/, wheels/ZIP/EXE/DLL, modele GGUF/BIN, runtime,
.env i warianty (oprócz pustego przykładu), klucze, bazy/WAL, załączniki,
nagrania, kopie, logi, reports, .venv i node_modules. Lokalna pełna paczka ZIP
zawiera oryginalny vendor dla instalacji; te binaria nie są częścią synchronizacji.

Potwierdzone testy: 77 Python i 33 JS zaliczone; 4 Windows pominięte.
Jawny brak testu nowej ścieżki pobierania Python na Windows oraz CUDA/VRAM/UI.
Źródła nie nadają projektowi nowej licencji. Własna licencja pozostaje niewybrana.
Szczegółowy wynik kontroli publikowanych plików: KONTROLA_PUBLIKACJI.md.

Właściciel 02.11.2026 zatwierdził wykonanie synchronizacji i kolejne zwykłe pushe
bez osobnych pytań. Aktualizacja main: fast-forward, z kontrolą oczekiwanego head.
Ten dokument jest częścią publikowanego zestawu; o wyniku operacji rozstrzyga
odczyt gałęzi GitHub po wysłaniu. Nie jest to odbiór Windows/CUDA.

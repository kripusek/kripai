# 01 — Serwer natywny Windows
Cel: RTX 3060 Ti 8 GB, Windows 11 x64, 32 GB RAM. Nie wymagamy WSL ani Dockera.
Program: %LOCALAPPDATA%\KripAI; prywatny Python, biblioteki i binaria llama.
Dane: %LOCALAPPDATA%\KripAI-data (SQLite/WAL, klucz LLM, modele, blokada).
Kopie: %LOCALAPPDATA%\KripAI-backups. ACL bieżący SID + SYSTEM; brak Everyone.
Nie instalujemy usługi systemowej, globalnego PATH, reguł zapory ani autostartu.

START kopiuje wyłącznie program, weryfikuje pakiety, instaluje zależności
lokalnie, uruchamia testy na oddzielnej bazie, pobiera model i startuje backend.
Microsoft VC runtime tylko gdy brakuje DLL; podpis Authenticode musi być ważny.
Jego instalator może wyświetlić systemowy UAC. Nie usuwamy współdzielonego
runtime Microsoft przy odinstalowaniu KripAI.

Backend posiada blokadę pliku przez cały czas pracy. Model jest jego procesem
potomnym, kontrolowanym uchwytem Popen; Windows Job Object kill-on-close
ogranicza pozostawianie procesu po awarii rodzica. Nie kończymy PID z pliku
ani wszystkich procesów python/llama na komputerze. WYLACZ używa prywatnego
znacznika plikowego i czeka na zwolnienie blokady; przy timeout zgłasza błąd.

Backup przy starcie, po zamknięciu i co 24 h pracy oraz BACKUP.cmd. Online
Backup API uwzględnia WAL; integrity_check i foreign_key_check przed publikacją.
14 ostatnich kopii, brak kopiowania 5 GB modelu. Przywrócenie wymaga zamkniętej
aplikacji, sprawdzenia zgodności schematu i kopii aktualnego stanu. Sesje po
restore są unieważniane; aktywne zadania nie są ponownie wykonywane.

Reset hasła jest lokalną operacją konta Windows, nie endpointem internetowym.
Nowe hasło 14–1024 znaków; stare sesje są usuwane. Kopie zawierają rozmowy i
hash hasła, nie są szyfrowanym sejfem; kopia na tym samym dysku nie chroni
przed awarią całego dysku. Można skopiować gotowy plik kopii na inny nośnik.

Etap 2: START próbuje pobrać przypięty Whisper CPU i model około 488 MB.
Niepowodzenie głosu nie blokuje tekstowego czatu. Whisper i System.Speech
pracują jako krótkotrwałe, pojedyncze procesy z Job Object oraz timeoutem.
Pliki voice-tmp pod prywatnym folderem danych są usuwane po każdym zadaniu,
a pozostałości po awarii przy kolejnym starcie. Backup nie zawiera audio.

Załączniki etapu 2.5a jako BLOB w tej samej SQLite; backup obejmuje oryginały i pochodne. Prywatny media-tmp sprzątany po zadaniu i na starcie. Szczegóły limitów: etap-2.5a/PLIKI.md.

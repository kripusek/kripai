# KripAI — obowiązująca specyfikacja Windows native
Aktualizacja zatwierdzona poleceniem właściciela 30.10.2026.
Pierwszeństwo: DECISIONS.md → 01–06 → etap-1/baza.sql i openapi.yaml → GAMING.md.
Starsza paczka WSL jest historyczna; jej PostgreSQL, Compose i Caddy nie są
zależnościami tej instalacji. Schematy urządzeń są projektami etapów późniejszych,
nie dowodem gotowej implementacji ani zatwierdzeniem publicznego dostępu.

- 01-core-server.md — procesy Windows, dane, backup, instalacja, granice.
- 02-agent.md — kontekst rozmowy i przyszłe narzędzia/RAG.
- 03-api.md — lokalne HTTP, sesje, idempotencja i SSE.
- 04-contracts.md — przyszłe urządzenia i zgody.
- 05-stack.md — biblioteki, modele, wersje i zasoby.
- 06-rollout.md — kryteria etapu 1 oraz plany etapów 2–6.
- etap-1/baza.sql — rzeczywisty schemat SQLite, atomowa migracja wersji 1.
- etap-1/openapi.yaml — kontrakt obecnego API.
- GAMING.md — automatyczny start/stop procesu modelu.
- schemas/ i examples/ — zachowane projekty komunikacji urządzeń; przed etapem 3
  przegląd i aktualizacja do oddzielnej, zabezpieczonej bramki zdalnej.

Kod i testy są przygotowane. Pełne zaliczenie etapu wymaga testów natywnego
Windows i CUDA na komputerze właściciela; raport określa wykonane próby.

Etap 2 rozpoczęty na kolejne polecenie właściciela: spec/etap-2/GLOS.md.
Jest to profil próbny CPU; odbiór PL/EN na Windows pozostaje niewykonany.

Etap 2.5a: etap-2.5a/PLIKI.md i atomowa migracja 002-pliki.sql.
Migracja 1 niezmieniona; przed aktualizacją istniejącej bazy automatyczna kopia.

Doprecyzowanie właściciela: zdjęcia w czacie i formatowanie — etap-2.5a/CZAT.md oraz migracja 003-obraz-w-rozmowie.sql.

Etap 2.5b rozpoczęty: etap-2.5b/RAG.md i 004-rag.sql. Tekstowe PDF,
E5 CPU i sqlite-vec; odbiór Windows i pełne benchmarki pozostają niewykonane.

Etap 4: etap-4/INTERNET_WTYCZKI.md — jawny plan internetu, GitHuba,
wyszukiwarki WWW, dalszych konektorów/MCP i operacji zapisu z uprawnieniami.

Pierwszy zakres MCP stdio: ../docs/MCP.md oraz etap-4/006-mcp.sql.

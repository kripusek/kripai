# KripAI — stan projektu
Aktualizacja: 02.11.2026. Ten plik opisuje bieżącą paczkę; STATUS.md zachowuje historię.

## Aktualny etap
Etapy 1, 2 i 2.5a mają implementacje. Odbiór natywnego Windows nieukończony.
Po odzyskaniu kodu dodano podstawowe kolorowanie kodu i bootstrap zależności
potrzebny do publikacji źródeł bez binarnego vendor. RAG 2.5b niezaimplementowany.

## Źródła i stan GitHub
Wejście: KripAI_Windows_native(4).zip (112 plików) oraz KripAI_HANDOFF(2).md.
GitHub: https://github.com/kripusek/kripai, publiczne repo, main:
65667aab5d5da25fbdf77b2f947786f560801a8e. Na moment audytu tylko README.md.
Git blob wejściowego README: c93436239ecf3266ae69f65045ee89068df170c1 — zgodny z GitHub.
Właściciel zatwierdził pierwszą synchronizację i kolejne zwykłe, sprawdzone pushe
bez osobnego pytania. Ten zestaw jest przygotowany jako pierwszy commit źródeł
na bazie powyższego main; zakres: docs/SYNC_GITHUB.md. Przed aktualizacją gałęzi
sprawdza się head i zachowuje nowszą pracę, bez force push. Wynik publikacji
można potwierdzić historią GitHub; opis nie zastępuje odczytu aktualnego head.

## Zaimplementowane
- Logowanie/sesje, CSRF/Origin/Host, historia i migracje SQLite, idempotencja.
- SSE/replay/cancel, paginacja, tokenizer kontekstu, ostrzeżenie output_limit.
- Proces potomny llama-server, przełączanie tekst/VLM, Gaming, backup/restore.
- STT Whisper CPU i TTS System.Speech; PNG/JPEG/PDF oraz obraz w wiadomości.
- Markdown, MathML, kopiowanie kodu; nowe podstawowe kolorowanie oznaczonych bloków.
- START: prywatny Python i wheels z ZIP albo pobierane przy braku z kontrolą SHA.
Szczegóły i granice: README.md, spec/, docs/AUDYT_2026-11-02.md.

## Potwierdzone wyniki
Bazowo: 76 Python (72 OK, 4 pominięte Windows) i 29 JS OK.
Po zmianach: 81 Python (77 OK, 4 pominięte Windows) i 33 JS OK; 110 zaliczonych.
Linux QA: Python 3.12.14, SQLite 3.53.1, FastAPI 0.115.12, Pydantic 2.14.1,
Pillow 12.3.0, pypdfium2 5.14.0. To nie jest runtime docelowego Windows.
SQLite, HTTP/SSE, dekodery i procesy potomne rzeczywiste. Inference i odpowiedzi
PyPI kontrolowane w testach. JS testuje model DOM. SHA 19 vendor i 2 Marked zgodne.
Pełny zapis: docs/WYNIKI_TESTOW.txt, najnowsza sekcja na końcu.

## Nieweryfikowane / ograniczenia
NIE URUCHOMIONO: Windows 11, prywatny CPython 3.13.17 z Pydantic 2.11.3/Pillow 13,
instalacja/ACL/Job Object/uninstall, CUDA/VRAM, mikrofon i System.Speech PL/EN.
Nowy bootstrap PowerShell nie wykonany ani nie sparsowany natywnie — brak PowerShell.
Próba wizualnego testu Playwright zablokowana przez brak binarium przeglądarki.
Pobieranie z prawdziwego PyPI nie zostało wykonane (testy kontrolowanego HTTP).
Brak deklaracji pełnego audytu bezpieczeństwa lub gotowości produkcyjnej.

Znane ograniczenia: skończony kontekst 4096/wyjście 2048; jedno zdjęcie na wiadomość;
brak analizy dawnych pikseli bez ponownego załącznika, całodokumentowego OCR,
RAG, trwałej pamięci i narzędzi. Lekki lexer nie pokrywa pełnej gramatyki języków
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
Baza, modele, limity GPU i migracje pozostały bez zmian.

## Następne zadania
1. Kontynuować zwykłe sprawdzone zmiany bez pytań o każdy push; aktualizować ten plik.
2. Windows / PowerShell: START.cmd i TESTY.cmd, potem Ctrl+F5. Osobno sprawdzić
   start z pełnego ZIP i czystych źródeł bez vendor; nie usuwać prywatnych danych.
3. Odbiór PL/EN, OCR, długiego kodu/kolorów/kopiowania, Gaming i pomiar VRAM,
   backup/restore/restart/uninstall według docs/INSTRUKCJA.md.
4. Etap 2.5b: przypiąć i sprawdzić sqlite-vec DLL oraz lokalny model embeddingów,
   następnie wdrożyć źródła/chunki/ACL, restart indeksowania, cytaty i backup.
   Nie zastępować sqlite-vec inną architekturą bez decyzji właściciela.

## Decyzje architektoniczne
Windows natywnie, localhost:8765, SQLite WAL, llama.cpp CUDA, RTX 3060 Ti 8 GB,
jeden model/jedna generacja, bez WSL/Docker/PostgreSQL/Caddy i płatnego API.
Dane/kopie poza programem; treść modelu/plików nie nadaje uprawnień.
Nie zwiększono kontekstu ani obciążenia VRAM. Dalsze decyzje: spec/DECISIONS.md.

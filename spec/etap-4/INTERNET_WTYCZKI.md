# Etap 4 — internet i integracje KripAI

Właściciel 02.11.2026 jawnie wymaga, aby dalszy plan obejmował dostęp AI do
internetu i wtyczek, w tym GitHuba. Priorytetem tego modułu jest odczyt.
Nie zmieniamy Windows/SQLite/llama.cpp ani nie dodajemy płatnego API inferencji.

| Krok | Zakres | Odbiór |
|---|---|---|
| 4a — odczyt | Publiczna strona HTTPS, publiczny README/issues GitHub, wyszukiwanie repozytoriów; lokalny model wybiera typowane narzędzie | Jawne przełączniki wiadomości, walidacja argumentów i zasobów, blokada localhost/LAN/metadata i DNS rebinding, limity, anulowanie, źródła, offline bez żądań sieciowych |
| 4b — wyszukiwarka WWW | Ogólne wyszukiwanie sieciowe z wybieranym dostawcą i odczytem wyników | Jawny dostawca/warunki/koszt; brak obowiązkowego płatnego API; zapytanie nie może wyciekać z prywatnej historii/OCR |
| 4c — konektory/MCP | Adaptery GitHub oraz kolejnych usług, także prywatnych po podłączeniu przez właściciela | Rejestr narzędzi i zakresów, bezpieczny magazyn poświadczeń, revoke, ACL; bez automatycznego uruchamiania dowolnych serwerów/skryptów MCP |
| 4d — zapis | Commity/PR/issues i inne zmiany w usługach | Zgoda właściciela na konkretny zakres może być trwała; deny-by-default poza zakresem, idempotencja, audyt, ochrona przed instrukcjami ze stron/repo |

Wtyczki ChatGPT nie są instalowane automatycznie w KripAI i nie udostępniają
mu tokenów tej rozmowy. Lokalny asystent potrzebuje własnych adapterów/API/MCP.
Odczyt publicznego GitHuba nie wymaga dodawania konta. Prywatne repozytoria
oraz zapis są kolejnym krokiem po jawnym podłączeniu własnych poświadczeń.

Pierwszy zakres 4a: internet domyślnie wyłączony; checkbox dla strony WWW i
osobny dla publicznego GitHuba. URL strony i repo muszą być podane w bieżącej
wiadomości. Zapytanie wyszukiwania repo musi być fragmentem tej wiadomości.
Model nie może wysłać prywatnego tekstu ze starej rozmowy/PDF jako nowego URL
lub zapytania. Odpowiedzi internetu są danymi, nie zgodami i nie definicjami
nowych narzędzi. Żaden tekst nie uruchamia shell ani operacji zapisu.

LLM planuje najwyżej dwa wywołania odczytu, wynik trafia do istniejącego
budżetu tokenów i końcowej odpowiedzi SSE. To pierwszy ograniczony agent,
nie pełna przeglądarka, wyszukiwarka WWW ani wykonywanie JavaScript stron.

## Implementacja pierwszego zakresu 4a
Kod: app/network.py (HTTPS/TLS/SSRF/parser), app/tools.py (rejestr/Pydantic/planer),
scripts/read_web.py (ograniczony proces), web/tools.js (przełączniki/źródła),
migracja 5 (flagi runu, sesja i źródła odpowiedzi). Bez nowych bibliotek/modeli.
llama-server tekstowy dostaje --jinja, oficjalny interfejs function calling b12000.
Planner dostaje wyłącznie bieżącą prośbę, nie historię ani PDF. Jeden lokalny
request planujący do 256 tokenów, do 2 typowanych odczytów, potem normalne SSE.
Po odczytach nie ma pętli kolejnych wywołań na podstawie niezaufanej strony.

web_read: HTTPS URL wskazany dosłownie w wiadomości. github_read: publiczne
README lub otwarte issues/PR wskazanego owner/repo. github_find: wyszukiwanie
publicznych repozytoriów GitHub, query musi być dosłownym fragmentem aktualnej
wiadomości. To nie jest jeszcze wyszukiwarka ogólnego internetu (krok 4b).

Wyniki mają do 1200 znaków i oznaczenie truncated. Trafiają jako niezaufane
JSON do systemowego kontekstu, podlegają temu samemu tokenizerowi i budżetowi
4096/2048. Przy braku miejsca tekst jest skracany, potem wyniki odrzucane.
Źródła [W1]/[W2], wycinki i odnośniki są zapisane w historii/backupie. Brak źródła
pokazuje jawny komunikat; błąd odczytu nie jest potwierdzeniem aktualnych danych.

Proces sieci: tylko GET, publiczny HTTPS/443, bez auth/cookies/sekretów/proxy,
bez JavaScript. DNS sprawdza wszystkie adresy i odrzuca m.in. loopback, LAN,
metadata, multicast i przejściowe adresy IPv6. Połączenie używa sprawdzonego
IP z zachowaniem TLS SNI i weryfikacji nazwy; nie rozwiązuje ponownie hosta.
Każde przekierowanie jest kontrolowane osobno, do 4 żądań. Do 512 KiB treści,
bez binariów i kompresji, socket timeout 5 s, cały proces 18 s/256 MiB, limit CPU
8 s w QA Linux. Job Object na Windows jest limitem zasobów, nie pełnym sandboxem.
Anulowanie/Gaming/utrata sesji kończy odczyt; pliki tymczasowe są usuwane.

Nie używamy zmiennych HTTP_PROXY/HTTPS_PROXY. Firmowy proxy i autoryzowane
strony nie są obsługiwane w tym zakresie. GitHub może ograniczyć publiczne
zapytania; 403/429 daje jawny błąd, nie zmianę serwisu czy ukryty token.

## Odbiór
Testy używają rzeczywistego SQLite/procesów/API modelu z kontrolowanymi wynikami
LLM i sieci. TLS/IP/redirecty i odmowy sprawdzane kontrolowanym transportem.
Próba prawdziwego GitHub GET na hostcie QA zakończyła się tool_dns_failed;
nie uznano jej za udane połączenie. Szczegóły: docs/INTERNET_TESTY.txt.
NIE URUCHOMIONO: Windows/Job Object tego procesu, prawdziwy Qwen3-8B wybierający
narzędzia i wizualny odbiór UI. Nie oznaczamy całego etapu 4 jako gotowego.

Windows: git pull --ff-only → START.cmd → Ctrl+F5. Włącz Publiczny GitHub,
wpisz „Przeczytaj README kripusek/kripai i streść go”. Sprawdź widoczny stan
odczytu i źródło. Dla WWW włącz Internet i podaj konkretny link HTTPS.
Potem przetestuj odczyt z wyłączonym przełącznikiem, Cancel/Gaming i niedostępny
serwis. Prywatne repo i zapis pozostają niedostępne bez następnego kroku integracji.

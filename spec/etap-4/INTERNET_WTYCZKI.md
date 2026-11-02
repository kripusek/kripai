# Internet i integracje — aktualny zakres 4a + pierwszy moduł 4b

Właściciel wymaga funkcji zbliżonych do ChatGPT: wyszukiwania i czytania stron,
GitHuba, a następnie kolejnych integracji. 02.11.2026 zgłosił działanie 4a poza
większymi stronami. Zastąpiono twarde odrzucanie dużych HTML odczytem częściowym
oraz dodano wyszukiwanie WWW. Nie obiecujemy dostępu do wszystkich serwisów:
logowanie, CAPTCHA, blokady, JavaScript i formaty binarne pozostają ograniczeniami.

| Krok | Stan / zakres | Odbiór |
|---|---|---|
| 4a — odczyt | WWW i publiczny GitHub, poprawiony odczyt dużych stron | Model i sieć na Windows, cancel/Gaming, SSRF, źródła, offline bez żądań |
| 4b — wyszukiwarka WWW | Pierwszy adapter Bing RSS bez klucza i bez płatnego API, następnie odczyt wyników | Jakość/rate limits na Windows; inni dostawcy/oficjalne API pozostają do rozbudowy |
| 4c — konektory/MCP | Plan: prywatny GitHub i kolejne usługi po podłączeniu właściciela | Własne poświadczenia KripAI, magazyn/revoke/ACL; bez wykonywania dowolnych serwerów z treści |
| 4d — zapis | Plan: commity/PR/issues i inne zmiany w zakresie zgody właściciela | Trwałe ograniczone uprawnienia, idempotencja i audyt, brak zgód z treści stron |

Wtyczki ChatGPT i ich tokeny nie przenoszą się do KripAI. Obecny GitHub jest
publiczny i bez logowania; prywatne repo/zapis wymagają własnej integracji.
Lokalne modele, Windows, SQLite i profil GPU pozostają bez zmian.

## Korzystanie
START.cmd po git pull --ff-only, potem Ctrl+F5. Internet domyślnie wyłączony.
Włącz „Internet: szukaj i czytaj”, wpisz pytanie bez URL, np. „Znajdź dokumentację
Pythona”, albo podaj konkretny link do streszczenia. Wyszukiwanie wysyła zapytanie
sformułowane na podstawie bieżącej prośby do Bing RSS; nie wysyłamy historii/PDF.
Dla publicznego GitHuba nadal jest osobny przełącznik i wskazane owner/repo.
Odpowiedź ma źródła [W1]/[W2] itd. Brak źródła jest jawnie oznaczony.

## Narzędzia i obieg
app/network.py: HTTPS/TLS/DNS/IP, parser strony i RSS. app/tools.py: typowany
rejestr, model planujący, lokalne notatki i cache na czas runu. scripts/read_web.py:
ograniczony proces sieciowy. web/tools.js: przełączniki i źródła.
Migracja 5 pozostaje bez zmian; ten moduł nie wymaga nowej migracji, biblioteki
ani modelu. Tekstowy llama-server b12000 nadal używa --jinja.

web_read: HTTPS URL z prośby lub z faktycznie otrzymanych wyników web_search.
web_search: Bing RSS, do 5 pozycji, bez konta/klucza i bez cichej zmiany dostawcy.
To publiczny kanał RSS do osobistego agregowania wyników, nie gwarantowane API
produkcyjne; obowiązują warunki i ograniczenia operatora. Na tym etapie nie ma
wyboru dostawcy ani obchodzenia blokad. Niedostępność daje jawny błąd.
github_read: README lub otwarte issues/PR wskazanego publicznego repozytorium.
github_find: wyszukiwanie repo po dosłownym fragmencie bieżącej prośby.

Planer dostaje wyłącznie aktualną prośbę i późniejsze wyniki publicznych narzędzi,
nie prywatną historię ani dokumenty RAG. Do 2 rund planowania, 4 wywołań odczytu,
jedno wyszukiwanie WWW i cache powtórnych argumentów. Nowe zapytania wyszukiwania
są dopuszczone tylko w pierwszej rundzie, zanim planer zobaczy wyniki internetu.
Druga runda może odczytać dozwolone źródła, ale nie wysłać nowego zapytania. Prawdziwy tokenizer rezerwuje
512 tokenów na plan. Pierwszy jawny URL jest odczytywany także wtedy, gdy model
pominie wywołanie. Wyniki wyszukiwarki rozszerzają listę dozwolonych URL tylko
po stronie backendu; tekst strony ani model nie mogą samodzielnie nadać uprawnień.

W drugim kroku model może odczytać wynik wyszukiwania. Finalna odpowiedź to
normalne SSE z istniejącym kontekstem 4096/wyjściem 2048. JSON źródeł jest
niezaufany; nie nadaje uprawnień shell/zapisu. Przy braku miejsca najpierw
ograniczamy źródła, nigdy nie pomijamy kontroli tokenów.

## Duże strony
Dawny limit 512 KiB pozostaje dla ścisłych odpowiedzi API/RSS/JSON, ale web_read
czyta strumieniowo do 8 MiB transmisji / 16 MiB po dekompresji gzip/deflate.
Duży Content-Length nie powoduje odrzucenia strony. Przy granicy zostaje
użyteczny prefiks i flaga zakresu częściowego. Nie usuwamy limitów RAM/czasu.

HTML: preferowane main/article, pominięte skrypty/style/nawigacja; do 160000 znaków
tekstu, obsługa charset i samodomykających się tagów. Bez uruchamiania JS.
Dla dłuższej treści lokalny LLM tworzy notatki z kolejnych fragmentów; każdy
fragment mierzy tokenizer. Do 8 żądań notatek po max 128 tokenów na cały run.
Obieg narzędzi ma budżet 150 s sprawdzany między operacjami (trwające HTTP ma
osobny timeout). Po wyczerpaniu budżetu notatek lub błędzie streszczenia zostaje
czytelny wycinek, zamiast udawanego pełnego odczytu lub automatycznej odmowy.

Metadane summary/processed_characters/document_characters/truncated rozróżniają
notatki od oryginału i pełny zakres od częściowego. To nie gwarancja jakości
streszczenia. W źródłach historii zapisujemy oryginalny wycinek do 1200 znaków,
nie wygenerowane notatki jako rzekomy cytat. Protokół procesu przyjmuje do 1 MiB
wyniku, aby pełny wyciąg tekstu nie wpadał w stary limit 16 KiB.

## Granice sieci i odbiór
Tylko GET, publiczny HTTPS/443, bez auth/cookies/sekretów/proxy. DNS/IP/redirecty
kontrolowane, połączenie do sprawdzonego IP z TLS SNI i walidacją nazwy.
Lokalne/LAN/metadata i przejściowe IP są blokowane także dla wyników wyszukiwania.
Socket timeout 5 s, proces odczytu 35 s / 256 MiB, CPU 8 s na Linux; Job Object
Windows to ograniczenie zasobów i życia, nie pełny sandbox. Cancel/Gaming/sesja
nadal kończą pracę. Nie ma obejść CAPTCHA, logowania ani blokad serwisu.

Kontrolowane testy: duży HTML, kompresja/bomby, charset, ekstrakcja, pełne przejście
przez lokalny HTTP modelu, wyszukiwanie → odczyt wyniku, oryginalne źródła,
cache/budżety i stare regresje. Raport: docs/WEB_SEARCH_TESTY.txt.
Dodatkowa próba pobrała i przetworzyła stronę Wikipedii >1 MiB oraz 5 prawdziwych
wyników RSS przez trasę urllib hosta QA. To nie test przypiętego transportu na
Windows. our-website-is-broken.org zwrócił Site Unavailable i nie został zaliczony.
Natywny Windows, rzeczywisty Qwen3-8B z nowym obiegiem i UI wizualny do odbioru.

## Rozpoczęty 4c — 02.11.2026
Adaptery, panel, pliki/katalogi GitHuba i opcjonalny lokalny DPAPI PAT są zaimplementowane.
Kontrakt, konfiguracja, testy, ograniczenia oraz kolejny zakres MCP: ../../docs/INTEGRACJE_4C.md.
MCP i zapis 4d nadal planem. Prywatne konto właściciela nieweryfikowane.

## Rozpoczęty 4d na kolejne polecenie właściciela
Lokalny github_draft, jawna publikacja w panelu do nowej gałęzi i PR, tylko
kripusek/kripusek-autoexec z lokalnym write_repositories/PAT. Bez merge/delete.
Kontrakt i ograniczenia: ../../docs/PR_I_DLUGIE_ODPOWIEDZI.md. MCP nadal planem.

## Kreator i uzgadnianie wyniku
Menu +, lokalny kreator DPAPI w UI i odczytowe sprawdzanie niepewnego PR:
docs/MENU_I_POLACZENIE_GITHUB.md i docs/UZGADNIANIE_PR.md w katalogu głównym.
MCP/OAuth z własną aplikacją nadal planem; istnieje działający kreator tokenu.

## Kopie dziennika 4d
Kopie i monotoniczny odzysk lokalnego dziennika opisuje docs/KOPIE_DZIENNIKA_GITHUB.md
w katalogu głównym. Przywrócenie danych nie zatwierdza ponownego zapisu do GitHuba.

## MCP stdio — wdrożony pierwszy zakres
Wcześniejsze zapisy „MCP nadal planem” opisują poprzednie paczki. Wbudowany
serwer dokumentacji, klient stdio, read-only narzędzia, zgoda, źródła i test
połączenia działają i przeszły rzeczywistą próbę CUDA. Nie jest to obsługa
dowolnych serwerów MCP. Granice i kolejny konkretny zakres: ../../docs/MCP.md.

## Oficjalna dokumentacja Pythona
web_search sprawdza indeks modułów Pythona dla zapytań o ich dokumentację;
nie zgaduje URL, rozróżnia link od odczytu i jawnie oznacza dostawcę/fallback.
Kontrakt i odbiór: ../../docs/DOKUMENTACJA_PYTHONA.md.

## Filtr site: egzekwowany przez backend
Zakres domen bieżącej prośby oraz query modelu ogranicza wyniki RSS i wybór
indeksu Pythona. Brak zgodnych wyników nie jest zastępowany obcymi stronami.
Kontrakt i testy: ../../docs/FILTR_DOMEN_WWW.md.

03.11.2026: gałęzie i ref dla README/file/tree wdrożone. Wcześniejszy
zakres „tylko domyślna gałąź” jest historyczny. Kontrakt: docs/GITHUB_REWIZJE.md
w katalogu głównym projektu.

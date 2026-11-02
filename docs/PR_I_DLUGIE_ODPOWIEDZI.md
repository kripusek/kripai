# Pierwszy zakres 4d i długie odpowiedzi — 02.11.2026

Właściciel zezwolił na następny krok: ograniczone gałęzie/PR dla
kripusek/kripusek-autoexec. Dostęp modelu do pozostałych usług nadal tylko odczyt.

## Długie odpowiedzi tekstowe

app/generation.py po finish_reason=length automatycznie kontynuuje odpowiedź.
Wszystkie porcje trafiają do tej samej wiadomości, SSE i historii SQLite.
Kontekst GPU pozostaje 4096; tokenizer dobiera ogon odpowiedzi i budżet następnej
porcji. Początkowe wyjście 2048, do 8 porcji, czyli najwyżej 16384 tokeny wyjścia.
Nie ma gwarancji nieskończonej odpowiedzi ani bezbłędnej ciągłości lokalnego LLM.
Po końcowym limicie nadal jest jawne ostrzeżenie i ręczne Kontynuuj.

Przy granicy model może urwać słowo lub linię. Niepełna końcowa linia jest
odtwarzana od ostatniej kompletnej granicy; snapshot SSE koryguje podgląd,
zamiast sklejać pół słowa z początkiem nowej listy. Przy błędzie transportu
otrzymany tekst pozostaje w historii z błędem inference_interrupted.
Cancel/Gaming sprawdzane także między porcjami. Nie zwiększono kontekstu/VRAM.
Ten mechanizm obejmuje odpowiedzi tekstowe; VLM/analiza obrazu nadal ma
dotychczasowy limit pojedynczego generowania i jawne oznaczenie niepełności.

## Lokalna propozycja i publikacja PR

1. Włącz GitHub i poproś o zmianę konkretnego małego pliku w
   kripusek/kripusek-autoexec, np. poprawę README.md.
2. Model ma sam odczytać plik i użyć github_draft. Narzędzie tworzy wyłącznie
   lokalną propozycję; do odczytu publicznego repo token nie jest potrzebny.
3. Rozwiń Integracje → Pokaż propozycje zmian. Zobaczysz konkretny unified diff.
4. Utwórz gałąź i PR publikuje propozycję na nowej gałęzi kripai/UUID. Nie ma
   aktualizacji main ani żadnej istniejącej gałęzi, merge, delete ani force push.

Pierwszy zakres obejmuje maks. 3 istniejące pliki tekstowe, każdy uprzednio
odczytany w całości (do 3000 znaków źródła). Nie edytujemy pliku na podstawie
samego streszczenia. Backend sprawdza SHA i przypina head gałęzi domyślnej,
zachowuje tryb 100644/100755, odrzuca symlinki, ukryte ścieżki i wybrane sekrety.
Przed publikacją ponownie sprawdza head; nowsza praca zatrzymuje publikację.
Nie uruchamiamy poleceń z repo, a PR uczciwie informuje o niewykonanych testach.
To pierwszy ograniczony moduł, nie autonomiczny edytor dowolnych repozytoriów.

## Poświadczenia lokalne

Windows / PowerShell:

```powershell
powershell -NoProfile -File .\scripts\configure-github.ps1
```

Wskaż kripusek/kripusek-autoexec, następnie TAK dla gałęzi i PR. Fine-grained
PAT ogranicz do tego repo, Contents Read and write i Pull requests Read and
write; ustaw termin ważności. Wklej PAT wyłącznie do lokalnego ukrytego monitu.
Skrypt zapisuje lokalną listę write_repositories i DPAPI CurrentUser.
Bez tej konfiguracji publikacja jest blokowana; lokalne propozycje nadal działają.
Nie korzystamy z tokenów ChatGPT ani poświadczeń agenta programistycznego.

Propozycje i dziennik publikacji są w osobnym SQLite github-changes.sqlite3
w prywatnym folderze danych. Dane są przypisane do owner. Po stanie published
ponowne kliknięcie zwraca ten sam wynik. Po publishing/outcome_unknown nie
ponawiamy ślepo POST; sprawdź wskazaną gałąź i PR w GitHub. Awaria może zostawić
gałąź bez PR lub obiekty Git bez gałęzi. Nie usuwamy ich automatycznie.
BACKUP.cmd dołącza teraz migawkę tego dziennika do kopii rozmów. Przywracanie
zachowuje nowsze wyniki i blokuje ponowienie niepewnych zapisów. Szczegóły:
KOPIE_DZIENNIKA_GITHUB.md. Odczytowe uzgadnianie wyniku jest dostępne w panelu.
POST publikacji wymaga sesji/CSRF/Origin/Host, model nie otrzymuje tego narzędzia.

## Weryfikacja

Testy regresji: prawdziwy SQLite/HTTP/SSE/procesy na Windows; kontrolowane API
GitHuba dla gałęzi/commita/PR, awarii, idempotencji, owner/CSRF i konfliktu head.
UI sprawdzone w kontrolowanym DOM, bez deklarowania wizualnego odbioru.
Dosłowny raport: WINDOWS_NASTĘPNY_KROK.txt.

Osobno rzeczywisty uruchomiony Qwen3-8B CUDA:
- wymuszone porcje 128 tokenów, 8 porcji → zakończona lista 30 wskazówek;
  test potwierdza kontynuacje, nie benchmark 16384 tokenów;
- publiczny README kripusek/kripusek-autoexec (903 znaki) → github_read →
  github_draft → rzeczywista lokalna propozycja w odizolowanym katalogu testowym;
- nie wysłano żadnego zapisu do GitHuba w tej próbie.

NIE URUCHOMIONO publikacji PR przez poświadczenia właściciela: konfiguracja
odczytu istnieje, ale write_repositories nie zezwala na zapis do autoexec.
Nie odszyfrowywano istniejącego tokenu w celu sprawdzania jego szerszych uprawnień.
Nie zaliczamy tego jako testu publikacji z prawdziwym kontem.
Odtwarzalna próba modelu: scripts/verify_next_stage.py przy uruchomionym backendzie.

Start po aktualizacji: WYLACZ.cmd → START.cmd → Ctrl+F5. Nie zmienia się model,
profil CUDA ani główny schemat bazy. MCP oraz trafniejszy dostawca wyszukiwarki
pozostają następnymi niezależnymi zadaniami.

## Poprawka planera po próbie 50 wskazówek

Samo włączenie Internet/GitHub nie oznacza konieczności użycia narzędzia.
Planer ma zwracać wywołanie lub krótkie „bez narzędzi”, zamiast pisać odpowiedź.
Wcześniej jego zwykła odpowiedź przekraczała 512 tokenów, co błędnie kończyło
cały run kodem tool_plan_limit. Teraz ucięty tekst planera bez tool_calls jest
pomijany i uruchamia się normalne generowanie z automatyczną kontynuacją.
Niepełne tool_calls nie są wykonywane: zostaje jawna informacja o braku odczytu,
przy zachowaniu wcześniejszych źródeł. Nie zwiększono limitów ani uprawnień.
Pusta lista wyników nie uruchamia już instrukcji odpowiedzi na podstawie źródeł:
zwykłe porady mają korzystać z wiedzy modelu. Test rzeczywistego CUDA ujawnił,
że poprzedni pusty kontekst sieciowy wywoływał nieuzasadnioną odmowę.

Regresja obejmuje kontrolowany HTTP/SSE i rzeczywisty SQLite z włączonymi
narzędziami oraz odrzucanie niepełnych argumentów przed jakąkolwiek siecią.
Próba dokładnej prośby właściciela na działającym modelu:
scripts/verify_plain_advice.py. Nie wymaga wyłączania przełączników internetu.

Źródła API:
https://docs.github.com/en/rest/git/trees#create-a-tree
https://docs.github.com/en/rest/git/commits#create-a-commit
https://docs.github.com/en/rest/git/refs#create-a-reference
https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request

Pełnej listy 50 punktów na CUDA NIE UKOŃCZONO w tej próbie: model generował
bardzo wolno przy 100% obciążenia GPU (7421/8192 MiB). Potwierdzono przejście
planera bez sieci; nie deklarujemy odbioru wszystkich 50 punktów. Zatrzymano
wyłącznie własny proces verify_plain_advice.py, bez zatrzymywania backendu/modelu.

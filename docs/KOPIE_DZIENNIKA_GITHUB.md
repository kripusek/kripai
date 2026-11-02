# Kopie propozycji i publikacji GitHuba — 02.11.2026

BACKUP.cmd, kopia przy uruchomieniu i automatyczna kopia dobowa obejmują teraz
także github-changes.sqlite3, jeżeli dziennik już istnieje. Nie zmienia się
główny format SQLite ani sposób uruchamiania programu.

## Pliki jednego zestawu

- `kripai-…sqlite3` — dotychczasowa baza rozmów, plików i RAG;
- `kripai-…sqlite3.github` — migawka dziennika propozycji i wyników publikacji;
- `kripai-…sqlite3.github.sha256` — kontrola integralności migawki dziennika.

Przenosząc kopię, zachowaj wszystkie trzy pliki obok siebie, bez zmiany nazw.
Jeśli dziennik jeszcze nie powstał, wystarczy dotychczasowy plik SQLite.
Poświadczenia GitHuba nie są dodawane do tych plików przez mechanizm kopii.

Obie bazy kopiowane są przez SQLite Online Backup API, również przy aktywnym
WAL. Pliki kopii mają journal_mode=DELETE, więc nie zależą od dodatkowych WAL/SHM.
Każda migawka jest spójna we własnej bazie; nie jest to wspólna transakcja dwóch
baz ani migawka stanu zdalnego GitHuba. Dziennik ma limit 256 MiB i limit czasu
kopiowania 20 s. Sprawdzane są integralność, schemat, dane i suma kontrolna.
Główny plik jest publikowany dopiero po zapisaniu kompletnego dziennika.
Awaria usuwa wyłącznie pliki tymczasowe nowego zestawu; stare kopie zostają.
Retencja 14 kopii usuwa też odpowiadające im pliki dziennika, nie obce pliki.

## Przywracanie bez ponawiania PR

PRZYWROC_KOPIE.cmd nadal wybiera główny plik. Program jest wtedy zatrzymany,
a przed zmianą danych powstaje kopia stanu bieżącego.

Dziennik jest scalany, zamiast cofać go do starszej wersji:

- istniejące, nowsze rekordy i ich wyniki pozostają;
- potwierdzenie published ma pierwszeństwo nad prepared/unknown, również
  gdy pochodzi z przywracanej kopii tego samego rekordu;
- brakujące potwierdzone publikacje są odzyskiwane jako published;
- brakujące nieopublikowane propozycje są odzyskiwane jako outcome_unknown;
  trzeba sprawdzić wynik w GitHub, nie można od razu ponownie wykonać zapisu;
- ten sam identyfikator z innym owner lub treścią przerywa operację bez
  zastąpienia bazy rozmów; transakcja dziennika zostaje wycofana;
- starsza kopia bez dziennika pozostawia bieżący dziennik bez zmian.

Uszkodzony lub niepełny zestaw nie jest przywracany. Sprawdzenie sumy nie jest
podpisem kryptograficznym: nie stanowi dowodu autorstwa kopii. Treść kopii
nie nadaje uprawnień do usług. Kopia z nieznanym schematem, niebezpieczną
ścieżką/repozytorium lub wyzwalaczami jest odrzucana. Jeżeli sam bieżący
dziennik jest uszkodzony, najpierw wymaga zabezpieczenia/diagnostyki pliku —
automatyczne naprawianie uszkodzonego źródła nie jest częścią tego modułu.

## Potwierdzone testy

Windows, prywatny CPython 3.13.17 i prawdziwy SQLite/vec0:
167/167 Python oraz 50/50 Node OK. Testy obejmują aktywny WAL, utratę dziennika,
odzysk published, blokadę ponowienia niepewnego zapisu, zachowanie nowszych
rekordów, stare kopie, konflikt, uszkodzenie/schemat/checksum, pełny dysk,
timeout, limit rozmiaru i retencję. Sieć nie jest potrzebna do tych testów.

Osobno wykonano rzeczywistą kopię działającej bazy właściciela z poprawnym
plikiem dziennika i SHA; zweryfikowano jeden rekord. Nie przywracano ani nie
usuwano danych właściciela. Poprawka jest zainstalowana lokalnie; aplikację
uruchomiono ponownie przy braku aktywnego generowania, backend i model są gotowe.
Poprzednie pliki programu mają kopię w prywatnym folderze kopii.

Nowe: app/github_backups.py, integracja w maintenance.py i test_github_backups.py.
Brak nowych zależności, migracji i zmiany profilu GPU. Dosłowny raport:
WINDOWS_KOPIE_GITHUB_TESTY.txt.

Dalej: odbiór rzeczywistego PR po lokalnej konfiguracji zapisu, MCP i trafniejszy
dostawca WWW. Konto i tokeny nie były zmieniane w tym module.

Źródła:
https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
https://www.sqlite.org/backup.html

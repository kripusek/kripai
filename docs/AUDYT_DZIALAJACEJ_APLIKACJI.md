# Audyt rzeczywistej aplikacji — 02.11.2026

Na polecenie właściciela sprawdzono jego uruchomioną instalację, zamiast
odsyłać go do kolejnej listy ręcznych prób. Pliki instalacji odpowiadały main.
Backend na 127.0.0.1:8765 i model na 127.0.0.1:8766 działały.

## Rzeczywista instalacja i konto

- Właściciel zalogował się lokalnie w osobnym oknie Chrome incognito.
  Hasła nie odczytywano z formularza ani nie zapisywano w plikach/logach.
- Menu „+”, Escape i okno Połączenia zadziałały w rzeczywistej aplikacji.
  Skrypty/CSS zwracały HTTP 200, moduły menu i integracji były załadowane.
- Rozmowa oznaczona „[Test KripAI]” zwróciła poprawne 391 i zachowała odpowiedź
  po zakończeniu SSE/odczycie historii. Pozostawiono tę oznaczoną rozmowę;
  nie usuwano ani nie zmieniano dotychczasowych rozmów właściciela.
- Istniejące zaszyfrowane poświadczenia GitHuba odszyfrowano wyłącznie w pamięci
  procesu do odczytowego testu API. GET konta i lokalnie wskazanego repo: OK.
  Nie wypisywano tokenu ani zawartości prywatnego repozytorium.
- Ustalono, że połączenie ma tylko odczyt: write_repositories nie jest włączone.
  Zapis/PR jest w tej konfiguracji celowo zablokowany. Nie rozszerzano uprawnień.
- Brak sesji → 401, obcy Origin → 403, obcy Host → 400.

## Rzeczywisty model, API i odizolowane dane

Dalsze próby wykonano przez ten sam kod API i rzeczywisty SQLite w osobnym
katalogu tymczasowym. Użyto rzeczywistego uruchomionego modelu CUDA i procesu
odczytu publicznego GitHuba. Sterownik trybu w tym procesie QA był kontrolowany:
nie zatrzymywano modelu właściciela ani nie przełączano jego Gaming/VLM.

| Próba | Wynik |
|---|---|
| 17 × 23, Internet i GitHub włączone | completed, 391, bez źródeł i błędów |
| README autoexec → odpowiedź | completed, 266 znaków, jedno źródło |
| README → lokalna propozycja PR | completed, dwa źródła, jedna propozycja |
| 50 ponumerowanych wskazówek | completed, 5245 znaków, wszystkie numery 1–50 |
| Anulowanie po rzeczywistym delta SSE | HTTP 202, cancelled; model nadal healthy |

Nie opublikowano żadnej gałęzi ani PR w ramach audytu. Dane prób odizolowanych
usunięto jako dane testowe; nie miały dostępu do bazy rozmów właściciela.
Nie deklarujemy osobnego ręcznego potwierdzenia dwóch zdań w każdym punkcie.

## Wykryta niejasność i poprawka

Panel nie mówił dostatecznie jasno, że połączone konto ma tylko odczyt,
a komunikat o brakującym zapisie odsyłał do starego skryptu PowerShell.
Status teraz jawnie opisuje ograniczenie publikacji, a błąd prowadzi do
„+ → Połącz GitHub / integracje”. Nie zmieniono uprawnień ani poświadczeń.
Dodano regresję UI. Poprawione dwa pliki interfejsu zainstalowano lokalnie po
sprawdzeniu zgodności starej wersji; kopia powstała w prywatnym folderze kopii.
Wystarczy odświeżyć stronę; backend i model nie wymagają restartu.

Regresja na Windows: 153/153 Python i 50/50 Node OK. Dosłowny raport:
WINDOWS_AUDYT_APLIKACJI_TESTY.txt. Syntetyczne modele w regresji pozostają
atrapami; wyżej wymienione próby GPU/sieci były osobnymi rzeczywistymi próbami.

NIE TESTOWANO jako zaliczonych w tej sesji: publikacja PR po włączeniu zapisu,
fizyczny mikrofon/odtwarzanie PL/EN, pełny zestaw VLM/RAG, uninstall oraz
Gaming zatrzymujący rzeczywisty GPU. Użytkownik wcześniej potwierdził Gaming;
automatyczne testy tych modułów przeszły, ale nie zastępują fizycznego odbioru.

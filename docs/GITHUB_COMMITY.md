# GitHub: historia i odczyt konkretnego commita

Włącz **+ → GitHub (odczyt)** i podaj repozytorium w bieżącej wiadomości.
Możesz zapytać „Pokaż ostatnie commity w kripusek/kripai” albo
„Przeczytaj commit PEŁNY_SHA w kripusek/kripai i opisz zmiany”.
Model wybiera narzędzie; samo włączenie GitHuba niczego nie pobiera.

`github_read section=commits` pokazuje do 10 najnowszych pozycji z pierwszej
porcji API. Opcjonalne `ref` wybiera gałąź, tag lub rewizję; pusty `ref` używa
domyślnej gałęzi. To ograniczony odczyt, a nie pełna historia repozytorium.
Pobieramy 11 pozycji, żeby wykryć dalszą historię. Wynik zawiera pełne SHA,
pierwszy wiersz opisu (do 200 znaków), nazwę autora i datę. Nie przekazujemy
strukturalnych pól email/login ani payloadu podpisu. Opisy pozostają niezaufaną
treścią źródła i mogą zawierać dane umieszczone w nich przez autora commita.

`section=commit` wymaga w `ref` pełnego SHA: 40 lub 64 znaki szesnastkowe.
Skrócony SHA i nazwa gałęzi nie są przyjmowane dla szczegółowego odczytu;
można najpierw odczytać historię. Porównujemy SHA odpowiedzi ze wskazanym.
Link źródła powstaje z dozwolonego repozytorium i zweryfikowanego SHA,
nie z adresów dostarczonych w JSON. Czytamy opis do 4000 znaków, SHA rodziców,
statystyki dodanych/usuniętych linii oraz do 20 plików pierwszej porcji API.
Każdy tekstowy patch ma limit 6000 znaków, dokument razem 130000 znaków.

Zmiany plików o nazwach wskazujących poświadczenia/prywatne bazy są pomijane,
również gdy taka jest poprzednia nazwa przemianowanego pliku. Brak patcha,
plik binarny, przekroczenie limitu oraz pominięte pliki są jawnie oznaczane.
Wynik ma `processed_files`, `text_patch_files`, `missing_patch_files`,
`omitted_sensitive_files`, `truncated` i `scope_note`. `total_files=null`
oznacza nieznaną całkowitą liczbę plików, a nie zero ani liczbę przetworzonych.
Nie gwarantujemy kompletnego diff: API może pomijać patche lub dalsze porcje.
Błąd HTTP/rozmiaru/formatu daje błąd, zamiast rzekomo pustej historii.

Długie dokumenty przechodzą przez istniejące lokalne streszczanie fragmentów.
Ograniczony budżet kontekstu może dalej ograniczyć zakres; jest to oznaczane.
Planer widzi tekst skrócony do 800 znaków z `feedback_text_truncated`;
lista nie jest dublowana przez pole `items`, żeby oszczędzać kontekst 4096.
Źródło nadal opisuje całą pobraną porcję do 10 wpisów. Z tego powodu prośba
o historię nie gwarantuje automatycznego odczytu patchy ostatniego commita;
można wskazać jego pełny SHA osobno.

Nowe operacje wykonują tylko GET. Commity i ich patche nie mają `editable`
i nie uprawniają do przygotowania propozycji edycji. Istniejąca osobna zgoda
na publikację PR nie jest zmieniana. Dane sieci nie zatwierdzają działań.
Publiczne repozytoria działają bez konta. Prywatne wymagają istniejącej lokalnej
konfiguracji DPAPI, listy repozytoriów oraz Contents: Read-only w tokenie.
Nie rozszerzamy uprawnień tokenu i nie prosimy o sekret w rozmowie.
Nowy prywatny zakres nie został przetestowany na koncie właściciela.

Windows: 314 testów Python (313 zaliczonych, 1 pominięty symlink), Node146/146.
Rzeczywisty proces potomny bez konta odczytał historię kripusek/kripai oraz
commit z trzema plikami i trzema patchami. Prawdziwy llama-server CUDA wybrał
narzędzie, zakończył odpowiedź (395 znaków) i zapisał właściwy URL źródła.
Konto i kontroler aplikacji były testowe; inferencja rzeczywista. Pomiar całej
karty po odpowiedzi: 7119/8192 MiB. To pojedynczy pomiar, nie benchmark.
Nie wykonywano zapisu do zewnętrznych usług. Raport: GITHUB_COMMITY_TESTY.txt.

Kod: app/github_commits.py, network.py, tools.py, context.py i błędy web/tools.js.
Bez nowych zależności i migracji. START.cmd, po aktualizacji Ctrl+F5.

Oficjalny kontrakt API: [GitHub REST commits](https://docs.github.com/en/rest/commits/commits).

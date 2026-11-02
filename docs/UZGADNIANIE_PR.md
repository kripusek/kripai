# Sprawdzenie wyniku publikacji — następny krok po menu i kreatorze

W oknie Połączenia → Propozycje zmian przy niepewnej operacji pojawia się
„Sprawdź wynik w GitHub”. To wyłącznie odczyt: nie powtarza tworzenia commita,
gałęzi ani PR i nie odblokowuje przycisku ponownej publikacji.

Backend sprawdza deterministyczną gałąź kripai/UUID, parent commita, dokładną
zawartość plików (Git blob SHA-1), zachowane tryby oraz brak dodatkowych zmian.
Następnie szuka PR o zgodnych head/ref/SHA i bazie. Wynik jest zapisywany
w rzeczywistym lokalnym SQLite, z zachowaniem owner i kontroli CSRF:

- PR potwierdzony → ten sam adres PR, bez nowego zapisu;
- gałąź potwierdzona, PR nie znaleziony → stan „Gałąź istnieje, brak PR”;
- brak gałęzi → wynik nadal niepewny; nie uznajemy tego za zgodę na ponowienie;
- zmieniona gałąź, nieoczekiwana odpowiedź lub inne zmiany → odmowa potwierdzenia.

Wynik potwierdzony przez równoległą publikację nie zostaje zastąpiony gorszym
wynikiem. Zamknięty PR też jest dowodem wcześniejszej publikacji, nie jest
automatycznie otwierany. Nie ma merge, usuwania ani force push.

Testy: rzeczywisty SQLite i kontrolowane API (wyłącznie GET), utrata odpowiedzi,
istniejący PR, sama gałąź, brak gałęzi, zmiana pliku, dodatkowy plik, owner/CSRF
i brak ponawiania mutacji. Interfejs sprawdzony testem DOM.
Rzeczywistego niepewnego PR właściciela NIE TESTOWANO — nie wywoływano celowo
awarii ani nie publikowano zmian w jego repozytorium. Nie użyto jego poświadczeń.

Kopie dziennika i zachowawczy odzysk opisuje KOPIE_DZIENNIKA_GITHUB.md.
Nadal do wykonania: szersze edycje,
OAuth po rejestracji własnej aplikacji GitHub, MCP i trafniejsza wyszukiwarka.
Struktura: app/github_changes.py, endpoint POST /integrations/github/drafts/{id}/reconcile,
web/integrations.js. Start nadal START.cmd, bez nowych zależności i modeli.

Źródła kontraktu:
https://docs.github.com/en/rest/git/refs#get-a-reference
https://docs.github.com/en/rest/git/trees#get-a-tree
https://docs.github.com/en/rest/pulls/pulls#list-pull-requests

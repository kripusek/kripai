# Zgłoszenia GitHub i komentarze — tylko odczyt

Przy włączonym GitHubie podaj `owner/repo` i numer zgłoszenia, np.
„Przeczytaj zgłoszenie #161233 w python/cpython i krótko podsumuj dyskusję”.
`github_read` ma `section=issue` z wymaganym dodatnim `number`; obsługuje
zgłoszenia otwarte i zamknięte. Nie nadaje uprawnień do propozycji plików ani zapisu.

Backend pobiera metadane → komentarze → metadane. Zmiana tytułu, opisu,
stanu, liczby komentarzy, updated_at lub etykiet odrzuca mieszany odczyt.
Nie jest to transakcyjna migawka komentarzy: ich późniejsza edycja pozostaje
możliwa. Ta granica jest zapisana w wyniku i tekście dla modelu.

Limity: opis 4000 znaków, tytuł 200, 8 etykiet po 60, do 10 pierwszych
komentarzy (API zwraca 11 dla wykrycia limitu), po 1500 znaków. Wynik zawiera
`processed_comments`, `total_comments`, `truncated`, `comments_error` i
`metadata_updated_at`. Brak komentarzy jest poprawnym wynikiem. Błąd dostępu
nie udaje pustej dyskusji; odpowiedź komentarzy ponad limitem API zachowuje
opis zgłoszenia i jawnie oznacza brak tej części. Źródła zgłoszenia i komentarzy
powstają ze wskazanego repo/numeru/ID, a nie z dowolnych URL zwróconych w JSON.

`section=issues` czyta pierwszą porcję do 21 ostatnio aktualizowanych otwartych
wpisów API i pokazuje do 10 zgłoszeń, pomijając PR. Ponieważ API łączy oba typy,
pominięcie PR oznacza częściową listę. Zero w tej porcji nie oznacza, że repo
nie ma żadnych zgłoszeń. Wybranie numeru PR jako issue daje czytelny komunikat
i wymaga użycia istniejącego `section=pull`.

Publiczny GitHub nadal działa bez konta. Prywatne zgłoszenia wymagają lokalnie
skonfigurowanego PAT z **Issues: Read-only**, ograniczonego do wybranych repo.
Kreator nowego tokenu proponuje ten odczyt; nie zmieniamy istniejącego tokenu
ani jego uprawnień. Zaznaczenie istniejącego zapisu PR nie włącza Issues: write.
Nie wklejaj tokenów do rozmowy. Konto prywatne nowego zakresu nie zostało zaliczone.

Weryfikacja: rzeczywisty ograniczony proces pobrał publiczne
`python/cpython#161233` i 1/1 komentarzy. Automatyczna regresja sprawdza zmiany
metadanych, brak dostępu, pomylenie PR, zły JSON/typy, limity i brak editable.
Raport: GITHUB_ZGLOSZENIA_TESTY.txt. Bez nowych zależności, migracji i metod zapisu.

Źródła: [Issues API](https://docs.github.com/en/rest/issues/issues),
[komentarze](https://docs.github.com/en/rest/issues/comments),
[parametry kreatora PAT](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

# Nazwy rozmów i eksport Markdown/JSON

Wybierz rozmowę z historii i otwórz **Rozmowa** w jej nagłówku. **Zmień nazwę**
otwiera formularz; zapis zmienia tylko tytuł, bez ingerencji w wiadomości,
źródła, szkic i aktualną generację. Tytuł po przycięciu ma 1–200 znaków w jednej
linii. Znaki sterujące i niepoprawne kodowanie są odrzucane. Błąd pozostawia
wpisaną nazwę do poprawienia; Escape zamyka formularz i przywraca fokus.

**Pobierz Markdown** oraz **Pobierz JSON** pobierają całą wybraną rozmowę.
Nazwy plików mają bezpieczny format `kripai-UUID.md/json`, niezależny od tytułu.
Eksport jest załącznikiem do pobrania, z `no-store` i `nosniff`. Wymaga sesji
i dostępu do konkretnej rozmowy. Nie wykonuje żądań do źródeł ani usług zewnętrznych.

Markdown zawiera pełny tekst wiadomości, role, daty UTC, nazwy/ID załączników
oraz wycinki i odnośniki źródeł W/D. JSON v1 ma `conversation` i `messages`;
wiadomości mają `attachments` z metadanymi oraz `sources` z `kind`/`label`.
Nie eksportujemy binariów, embeddingów, haseł, sesji, tokenów i prywatnej
konfiguracji programu. To nie pełna kopia danych ani format importu całej bazy.
Surowa treść rozmowy może zawierać niezaufany Markdown/HTML — pobranie nie
uruchamia go w aplikacji. Lokalne odnośniki MCP nadal wymagają działającej
aplikacji, sesji i aktualnego zakresu folderu; eksport nie archiwizuje tych plików.

Zapisujemy cały wynik albo zwracamy jawny błąd: limit wyniku 8 MiB i 10000
wiadomości, bez cichego obcinania. Czytamy spójny snapshot SQLite, iterując
wiadomości i źródła, bez rezerwowania blokady zapisu. Zmiana nazwy odbywa się
w osobnej krótkiej transakcji z kontrolą właściciela.

API: PATCH `/api/v1/conversations/{id}` z `{title}` (sesja, Origin i CSRF), GET
`/api/v1/conversations/{id}/export?format=md|json` (sesja). Nieznana i obca
rozmowa odmawiają dostępu. Zmiana rozmowy/logout unieważniają stare wyniki UI.
Nowa rozmowa przyjęta już po wylogowaniu nie odtwarza starego widoku.

Chrome/Playwright na izolowanym rzeczywistym API potwierdził zmianę polskiej
nazwy, aktualny tytuł w historii, pobranie obu formatów z pełnym tekstem 16404
znaków i źródłem W1, zachowanie szkicu, Escape/fokus, logout i mobilne 390 px.
Nie wysłano wiadomości ani nie uruchamiano modelu. Raport: ROZMOWY_EKSPORT_TESTY.txt.

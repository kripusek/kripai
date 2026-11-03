# Nowa rozmowa od zapisanej odpowiedzi — kontrakt

Implementacja: `app/conversation_branch.py`, trasa w `app/main.py`,
`web/conversation-branch.js` i integracja w `web/app.js`.

## Działanie

Pod zapisaną odpowiedzią asystenta jest przycisk „Nowa rozmowa od tej odpowiedzi”.
Pojawia się dla wiadomości z prawidłowym UUID w aktualnie otwartej rozmowie,
także po załadowaniu starszej historii. Nie jest dodawany do wiadomości użytkownika
ani do niezapisanej, strumieniowanej odpowiedzi. Zakończenie generowania przeładowuje
zapisane wiadomości, co udostępnia działanie pod gotową odpowiedzią.

Jawne kliknięcie tworzy nową rozmowę zawierającą wiadomości od początku oryginału
do wybranej odpowiedzi **włącznie**, według kolejności `messages.seq`.
Późniejsze wiadomości pozostają wyłącznie w oryginale. Oryginalna rozmowa i jej
wiadomości nie są zmieniane ani usuwane. Kopie dostają nowe UUID i nowe numery
`seq`; zachowują role, pełną treść oraz daty oryginalnych wiadomości.
`client_message_id` kopii jest pusty. Nowa rozmowa otrzymuje własną datę utworzenia
i nazwę z przyrostkiem „ — nowa gałąź”, ograniczoną do 200 znaków.

Operacja nie uruchamia modelu, nie wysyła wiadomości i nie wykonuje odczytów sieci,
GitHuba ani lokalnych dokumentów. Nie kopiuje przebiegów `runs`, zdarzeń generacji,
historycznych zezwoleń na narzędzia ani dawnych identyfikatorów sesji. Cytaty ze
źródeł są zapisanymi danymi i nie nadają uprawnień do nowych działań. Bieżące,
jawne ustawienia narzędzi w interfejsie pozostają ustawieniami użytkownika;
kopiowanie historii nie odtwarza ustawień z oryginalnej generacji.

## Źródła i pliki

- Źródła W: kopiowane są zapisane numery, nazwy narzędzi, adresy, tytuły i wycinki
  `tool_sources`. Nie następuje ponowne pobranie stron ani sprawdzanie ich aktualności.
- Źródła D: kopiowane są numery, identyfikatory dokumentów, strony i wycinki
  `message_sources`, wyłącznie dla załączników należących do właściciela rozmowy.
- Obrazy: kopiowane są referencje `message_images` do własnych załączników.
  Powiązanie obrazu z sesją wskazuje aktualną sesję tworzącą nową rozmowę.
  Dawna sesja nie jest kopiowana.

Pliki są współdzielone przez referencje do istniejących rekordów `attachments`.
Nie powstają duplikaty binariów, podglądów ani dodatkowe rekordy załączników.
Obce lub usunięte załączniki nie są przenoszone. Usunięcie współdzielonego pliku
wpływa na jego dostępność we wszystkich rozmowach odwołujących się do tego pliku.
Zmiana aktualnej strony lub podglądu tego załącznika również dotyczy obu rozmów,
ponieważ nowa rozmowa nie przechowuje niezależnej kopii stanu pliku.

## Sesja, idempotencja i limity

Tworzenie wymaga zalogowanego właściciela oraz aktualnej, niewygasłej i nieodwołanej
sesji. Obowiązują standardowe kontrole lokalnego Host, Origin i CSRF. Obca lub
nieistniejąca rozmowa oraz punkt spoza wskazanej rozmowy dają ten sam błąd 404.
Wiadomość użytkownika we własnej rozmowie nie może być punktem rozgałęzienia.

W jednym prefiksie można skopiować najwyżej 1000 wiadomości i 8 MiB treści
`messages.content` liczonej jako bajty UTF-8. Limit tekstu nie obejmuje binariów
współdzielonych załączników. Przekroczenie limitu kończy się jawnym błędem;
prefiks nigdy nie jest po cichu skracany. Aktywny przebieg w źródłowej rozmowie
blokuje operację. Aktywny przebieg w innej rozmowie nie blokuje helpera backendu;
interfejs dodatkowo blokuje przyciski podczas bieżącego generowania.

Kopiowanie oraz zapis potwierdzenia idempotencji należą do jednej transakcji
SQLite. Nieudana operacja wycofuje wszystkie kopie i potwierdzenie. Ten sam klucz
UUID dla tego samego właściciela, adresu trasy i treści żądania zwraca wcześniej
utworzoną rozmowę zamiast tworzyć kolejną. Klucz jest przechowywany przez 24 godziny.
Ponowne użycie klucza z innym `message_id` daje konflikt 409. Odczyt potwierdzenia
ponownie sprawdza bieżącą sesję i własność utworzonej rozmowy.

Przycisk zachowuje swój klucz po utracie odpowiedzi i podczas ponownego kliknięcia.
W trakcie żądania wszystkie przyciski rozgałęziania są zablokowane. Zmiana rozmowy
lub wylogowanie unieważniają spóźnione wyniki; stary przycisk nie może otworzyć
rozmowy w nowym kontekście. Klucz dotyczy danego przycisku w bieżącym widoku;
nie ma obietnicy wznowienia tej samej operacji po pełnym przeładowaniu strony.

## API

`POST /api/v1/conversations/{cid}/branch`

Wymagane nagłówki: aktywna sesja cookie, `Origin`, `X-CSRF-Token`,
`Idempotency-Key` jako UUID i `Content-Type: application/json`.

```json
{"message_id":"UUID zapisanej odpowiedzi asystenta"}
```

Sukces oraz odtworzenie potwierdzenia: HTTP 201.

```json
{
  "id": "UUID nowej rozmowy",
  "title": "Tytuł — nowa gałąź",
  "created_at": 1793700000.0,
  "copied_messages": 2
}
```

Istotne błędy:

| HTTP | Kod | Znaczenie |
| --- | --- | --- |
| 401 | `login_required` | Brak aktualnej sesji. |
| 403 | `csrf_invalid` / `origin_denied` | Nieprawidłowy CSRF lub Origin. |
| 404 | `not_found` | Brak własnej rozmowy lub wskazanego punktu w tej rozmowie. |
| 409 | `generation_busy` | Trwa generowanie w źródłowej rozmowie. |
| 409 | `idempotency_conflict` | Ten klucz został już użyty z innym żądaniem. |
| 413 | `branch_too_large` | Prefiks przekracza 1000 wiadomości lub 8 MiB tekstu. |
| 422 | `branch_point` | Punkt nie jest odpowiedzią asystenta. |
| 422 | `idempotency_key_required` | Brak prawidłowego klucza UUID. |
| 500 | `branch_invalid_data` | Nieprawidłowy typ zapisanych danych źródłowych. |

Błędy kształtu JSON i UUID parametrów przechodzą standardową walidację API.

## Interfejs i ograniczenia bieżącej integracji

`KripConversationBranch.configure({api,onBranch,notice})`, `setContext(cid,reset)`,
`setBusy(bool)`, `clear()` i
`attach(container,{conversationId,messageId,role})` tworzą warstwę przycisku.
`api` dostaje lokalną ścieżkę, metodę POST, treść i stabilny klucz idempotencji.
Odpowiedź jest walidowana przed `onBranch`; nie jest interpretowana jako HTML.

Po sukcesie integracja otwiera nową rozmowę. Tekst niewysłanego szkicu w polu
wiadomości pozostaje zachowany; nic nie jest automatycznie wysyłane. Aktualny
`load()` czyści jednak niewysłany załącznik obrazu przy zmianie identyfikatora
rozmowy. Ochrona szkicu obejmująca taki obraz wymaga osobnej poprawki integracji.

`load()` zwraca wynik otwarcia historii. Jeżeli tworzenie w backendzie się uda,
ale pobranie historii lub listy rozmów zawiedzie, interfejs rozróżnia te wyniki:
„Nowa rozmowa została utworzona, ale nie udało się jej otworzyć. Kliknij Najnowsze,
aby ponowić odczyt.” Czyści nieaktualny widok, odświeża listę i udostępnia przycisk
ponowienia odczytu bez ponownego tworzenia gałęzi.

## Weryfikacja

Kontrakt pokrywają zestawy `tests/test_conversation_branch.py`,
`tests/test_conversation_branch_api.py` i `tests/test_conversation_branch_ui.cjs`.
Windows: 302 testy Python (301 zaliczonych, 1 pominięty), Node 134/134.
Rzeczywisty Chromium oraz izolowane API/SQLite: utrata odpowiedzi po HTTP201
i ponowienie z tym samym kluczem tworzą jedną gałąź. Prefiks, W1, nowe ID,
oryginał, tekst szkicu i mobile390 sprawdzone. Osobno błąd GET po utworzeniu
i ponowienie odczytu. Raport: ROZMOWY_GALEZIE_TESTY.txt. Konto i kontroler
testowe; nie uruchamiano nowej inferencji CUDA ani prób głosu.

# MCP: folder dokumentów właściciela

Opcjonalny adapter `mcp_files` uruchamia rzeczywisty, oficjalny serwer
`@modelcontextprotocol/server-filesystem` 2.1.0 przez stdio. Wbudowane `mcp_docs`
nadal czyta dokumentację KripAI bez Node.js, konta i internetu.

W menu **+ → Połączenia** wybierz **Przygotuj serwer MCP**, następnie wpisz
istniejący bezwzględny folder dokumentów, nazwę połączenia i wybierz **Wybierz
folder → Test odczytu**. Przygotowanie wymaga Node.js 24+ zainstalowanego
w `Program Files\nodejs` oraz jednorazowego dostępu do publicznego npm.
Pozostałe funkcje KripAI nie wymagają Node. Nie używamy `npx`, `latest`,
kont npm, tokenów ani skryptów instalacyjnych pakietów.

Przy wiadomości włącz **MCP: dokumenty** w menu +. Przykład:
„Przeczytaj przez mcp_files plik notatki.md z mojego folderu”. Możesz najpierw
poprosić o listę dokumentów. Nazwy ze spacjami podawaj w cudzysłowie.
Zgoda jest domyślnie wyłączona; samo połączenie nie wysyła plików do modelu.

## Granice

- Tylko `list_directory`, `read_text_file` i `search_files`, sprawdzone także przez adnotacje
  serwera. Model nie dostaje surowego RPC, poleceń programu ani metod zapisu.
  Oficjalny serwer udostępnia również zapis: klient KripAI go nie wywołuje.
  To kontrola klienta, nie systemowy sandbox dla dowolnego złośliwego programu.
- Jeden jawnie wybrany folder, `.md`/`.txt` do 32 KiB, tekst do 12000 znaków
  z jawną flagą przycięcia i oryginalnym wycinkiem do 1200 znaków w źródłach.
  Listowanie bez rekursji, katalog do 200 pozycji, ścieżka do 200 znaków/6 poziomów.
- Brak ukrytych plików/katalogów, symlinków, junction, UNC, ścieżek `..`,
  strumieni ADS i dostępu do folderów danych/kopii KripAI oraz ich przodków.
  Wybierz osobny folder przeznaczony do udostępnienia modelowi. Rozszerzenie
  pliku nie zapewnia braku sekretów w jego treści.
- Folder musi być wybrany lokalnie przez właściciela; tekst dokumentu i model
  nie zmieniają konfiguracji ani zgód. Model i historia źródeł dostają ścieżki
  względne, nazwę połączenia i losowy identyfikator zakresu. Bezwzględna ścieżka
  pozostaje w prywatnej konfiguracji, API właściciela i argumentach procesu Node.
- Zmiana/odłączenie folderu unieważnia wcześniejszy zakres i stare URL źródeł.
  Poprzednia konfiguracja jest kopiowana do folderu kopii przed zmianą.
- Proces ma minimalne środowisko bez tokenów, stderr nie jest logowany,
  timeout 15 s, ramkę do 256 KiB, Job Object 128 MiB. Zewnętrzny proces odczytu
  zachowuje dotychczasowy limit 35 s i anulowanie całego drzewa procesów.

## Instalacja i kontrola

`scripts/setup_mcp_filesystem.py` pobiera wyłącznie zależności z przypiętego
`scripts/mcp-filesystem/package-lock.json` (`npm ci --ignore-scripts`). Wymagane
HTTPS registry.npmjs.org i integralność SHA-512; npm dostaje puste npmrc i osobny
cache. Sprawdzamy lokalny inwentarz SHA-256 przed uruchomieniem. Nieznany folder
runtime nie jest nadpisywany; znany poprzedni pakiet jest zachowywany.
Modele i pakiety Node nie trafiają do repozytorium. Licencje pozostają w
zainstalowanym pakiecie; projekt upstream wskazuje `SEE LICENSE IN LICENSE`.

API: `/integrations/mcp-files/config` GET/POST, `/prepare`, `/test`, `/disconnect`
POST (owner, sesja i CSRF przy zmianach), `/catalog` i `/document` GET (sesja,
`root` UUID i względny `path`). Błędy są stałymi kodami bez surowego stderr.

Nie jest to dowolny katalog serwerów MCP, OAuth ani dostęp do prywatnego konta.
Kolejny zakres: drugi konkretny dostawca odczytowy z własnym kontraktem zgód,
limitem danych i rzeczywistym testem, przed ewentualnym ogólnym rejestrem.

## Wybór dokumentu bez wpisywania ścieżki

W **+ → Połączenia → Przeglądaj dokumenty** przechodź do podkatalogów lub
użyj **Katalog wyżej** i **Folder główny**. **Otwórz źródło** otwiera tekst
w nowej karcie wymagającej sesji. **Zapytaj o dokument** dopisuje względną
ścieżkę do bieżącego szkicu (albo przygotowuje pytanie o podsumowanie), włącza
MCP i przenosi fokus do wiadomości. Wysyłasz ją samodzielnie. Przeglądanie
katalogu nie uruchamia modelu ani nie czyta automatycznie treści plików.

Obowiązują dotychczasowe limity i identyfikator wybranego folderu. Pominięte
pozycje są zliczane; błąd serwera jest pokazany zamiast rzekomo pustej listy.
Przy wylogowaniu/zmianie root lista i stare przyciski są unieważniane. Nie
usuwamy istniejącego szkicu ani zdjęcia; zdjęcie trzeba odłączyć przed tym
wyborem dokumentu. Inne zgody wiadomości pozostają zgodne z wyborem użytkownika.

Wyszukiwanie nazw i dodatkowa odczytowa metoda search_files: [kontrakt](MCP_WYSZUKIWANIE.md).

Drugi konkretny dostawca stdio jest wdrożony: [czas i strefy](MCP_CZAS.md).
Wspólna zgoda w menu ma teraz nazwę „MCP: dokumenty i czas”.

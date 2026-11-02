# Gałęzie, tagi i commity — odczyt GitHuba

03.11.2026. Włącz GitHub pod + i wskaż owner/repo w bieżącej wiadomości.
Możesz poprosić o listę gałęzi albo odczyt README/pliku/katalogu z określonej
gałęzi, tagu lub SHA commita. Bez ref nadal używana jest domyślna gałąź.

github_read otrzymał section=branches i opcjonalny ref dla readme/file/tree.
Lista pokazuje do 20 gałęzi wraz z SHA; pobieramy 21, by jawnie oznaczyć
istnienie dalszych wyników. Nie ma automatycznej paginacji. Referencja jest
kodowana w parametrze API i źródle odpowiedzi. Źródło starej rewizji nie
wskazuje błędnie HEAD. Dopuszczone są także nazwy gałęzi z ukośnikiem/Unicode;
kontrole i niedozwolone wyrażenia rewizji są odrzucane przed odczytem.

Odczyt jawnie wskazanego ref nie ustawia editable i nie zasila listy plików
uprawnionych do lokalnej propozycji zmian. Propozycja nadal wymaga osobnego
pełnego odczytu pliku z bieżącej domyślnej gałęzi i dotychczasowych kontroli
SHA oraz uprawnień. Nie dodano żadnego endpointu zapisu ani nowego zakresu PAT.
Token pozostaje lokalny w DPAPI; publiczne repo działa anonimowo.

Nadal obowiązuje 512 KiB odpowiedzi API, limit tekstu/kontekstu i częściowe
notatki przy dużym dokumencie. Nie obiecujemy pełnego odczytu dowolnego pliku.
Prywatny dostęp w tym module testowany kontrolowanym adapterem; nie udajemy
testu nowego prywatnego konta. Hasła/tokeny nie trafiają do modelu.

Windows: 206 testów Python (205 OK, 1 symlink pominięty), Node 53/53.
Rzeczywisty proces odczytał anonimowo gałęzie kripusek/kripai, README.md
(13801 znaków wyciągu) i katalog app z commita 60c504b8ec677fbc255e6070b717291dda42026f.
Nie oznacza to przetworzenia całego tekstu przez model. Dosłowna regresja:
GITHUB_REWIZJE_TESTY.txt. Inference regresji kontrolowane, procesy/SQLite realne.

Kod: app/tools.py, app/network.py, tests/test_github_refs.py. Start START.cmd,
bez migracji/zależności i zmian GPU. Dalej: odczyt PR i ich zmian, zewnętrzny MCP.

Kontrakty: [Contents API](https://docs.github.com/en/rest/repos/contents),
[lista gałęzi](https://docs.github.com/en/rest/branches/branches).

Natywna próba wykryła 30-sekundowy ReadTimeout planera w profilu f16.
Profil tekstowy używa teraz Flash Attention on oraz KV K/V q8_0 (bez zmiany
GGUF/kontekstu 4096/wyjścia 2048). Flagi sprawdzone w lokalnym b12000 --help.
Po zmianie rzeczywisty CUDA/Qwen3-8B odczytał wskazany commit i zakończył
odpowiedź ze źródłem (452 znaki). Start modelu w próbie 5.248 s, cała karta
7322/8192 MiB po odpowiedzi. Nie jest to benchmark jakości ani dowód przyczyny
każdego timeoutu. Model VLM zachowuje własny dotychczasowy profil.

Dodatkowo prawdziwy Qwen3-8B z q8 KV: poprawne 391 na 17×23; generacja
przerwana po rzeczywistej delcie, run=cancelled, model pozostał gotowy.
Kontroler trybu i konto w tych próbach były odizolowanymi fixture, inference
i CUDA rzeczywiste. Nie zatrzymywano modelu właściciela przez Gaming.

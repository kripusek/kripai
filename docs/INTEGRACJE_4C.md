# Integracje 4c — pierwszy zakres, 02.11.2026

Wspólny kontrakt ReadAdapter (read/status) i mapa TOOL_ADAPTERS kierują
wywołania procesu sieciowego do adapterów WWW/GitHub. Nadal tylko GET.
Panel przy przełącznikach internetu pokazuje konfigurację i testuje odczyt
katalogu repo przez ten sam ograniczony proces. Test nie wymaga modelu.
Endpointy wymagają sesji, POST także CSRF i dotychczasowych kontroli Origin/Host.

github_read obsługuje readme/issues/file/tree oraz path. file/tree używają
domyślnej gałęzi; tree listuje jeden katalog, do 200 wpisów, bez rekursji.
Model może wybierać ścieżki wyłącznie we wskazanym w bieżącej prośbie repo.
Limit odpowiedzi API 512 KiB pozostaje: większy plik/katalog może zostać odrzucony.
Nie są obsługiwane binaria, dowolne rewizje ani zapis do usług.

## Opcjonalny prywatny GitHub

Windows / PowerShell:

```powershell
powershell -NoProfile -File .\scripts\configure-github.ps1
```

Najpierw START.cmd przygotowuje prywatny folder danych z ACL. W GitHub utwórz
fine-grained PAT ograniczony do wybranych repozytoriów: Contents Read-only,
Metadata wymagane przez GitHub, opcjonalnie Issues Read-only. Ustaw datę wygaśnięcia.
Token wpisuj wyłącznie w lokalnym ukrytym monicie skryptu, nigdy w rozmowie.
Skrypt zapisuje github.json w LOCALAPPDATA/KripAI-data, szyfrując token DPAPI
CurrentUser. Dostęp wymaga jednocześnie repo z listy lokalnej i bieżącej prośby.
Publiczne repo poza listą nadal działa anonimowo. Token nie trafia do pliku
żądania procesu, argv, modelu ani logów. Authorization tylko do api.github.com;
uwierzytelnione przekierowania są odrzucane. Cofnięcie: usuń github.json oraz
unieważnij PAT w GitHub. Konfiguracja poświadczeń nie jest częścią backupu SQLite.
DPAPI nie izoluje od innych programów działających na tym samym koncie Windows.

Brak poświadczeń właściciela: test rzeczywistego prywatnego repo NIE URUCHOMIONO.
Nie użyto kont ani tokenów ChatGPT. Test DPAPI używa wyłącznie sztucznej wartości.

## MCP — kolejny konkretny zakres

MCP pozostaje planem, nie gotową integracją. Następny moduł: jeden ręcznie
skonfigurowany lokalny serwer stdio, jawna lista read-only tools, mapowanie
tools/list i tools/call na ReadAdapter, ograniczony proces/timeout/cancel,
walidacja JSON i limitów wyników, odrzucanie zapisu oraz dynamicznych adresów
serwerów z modelu/stron. Poświadczenia pozostają po stronie adaptera.
Odbiór: prawdziwy serwer MCP, odczyt, rozłączenie, timeout, błędny protokół,
próba narzędzia spoza listy i test braku sekretów w kontekście. Instalowanie
lub uruchamianie dowolnego programu wskazanego przez model jest zabronione.

## Potwierdzona weryfikacja Windows

CPython 3.13.17, SQLite 3.50.4. Przed zmianami 123/123 testów Python OK;
testy JS 43 zachowań OK (Node raportuje też dom.cjs jako 44. plik testowy).
Pierwsza próba nie miała DLL w checkout: skopiowano lokalną vec0.dll;
loader sprawdził SHA z locka. Binarium nie jest publikowane.
Pełny raport końcowy: WINDOWS_4C_TESTY.txt.

Rzeczywisty llama-server.exe CUDA, lokalny Qwen3-8B, kontekst 4096:
model wybrał github_read, prawdziwe README publicznego kripusek/kripai
odczytane w procesie, streszczone fragmentami, odpowiedź wygenerowana.
Źródło https://github.com/kripusek/kripai#readme. Całkowity VRAM podczas
próby 7378/8192 MiB; przed próbą 2199 MiB. To pomiar całej karty, nie samego modelu.
Proces testowy zamknięto. Nie zmieniono portu ani danych działającego backendu.

Rzeczywisty Bing RSS: 5 wyników; odczyt wyniku https://www.python.org/doc/
dał 1824 znaki. Wikipedia: tool_network_failed, także poza sandboxem.
Duże HTML/gzip/deflate, limity, notatki, cancel/Gaming, błędy i źródła
sprawdzone regresją z kontrolowanym HTTP/LLM. Nie jest to zaliczenie cancel
podczas rzeczywistej generacji CUDA ani wizualnego UI. Nie zaliczono mikrofonu,
instalacji/uninstall, wszystkich stron, CAPTCHA, logowania ani JavaScript.

Źródła kontraktów:
[GitHub Contents API](https://docs.github.com/en/rest/repos/contents),
[Microsoft DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata).

## Aktualizacja: pierwszy zakres MCP wdrożony
Wcześniejsza sekcja „kolejny konkretny zakres” jest historyczna. Działa lokalny
serwer dokumentacji stdio, klient, tools/list/call, zgoda, źródła i test połączenia.
Nie udostępniamy jeszcze konfiguracji dowolnego programu dostawcy. Pełny kontrakt,
rzeczywisty test CUDA i następny zewnętrzny dostawca: [MCP.md](MCP.md).

03.11.2026: gałęzie i ref dla README/file/tree wdrożone. Wcześniejszy
zakres „tylko domyślna gałąź” jest historyczny. Kontrakt: docs/GITHUB_REWIZJE.md
w katalogu głównym projektu.

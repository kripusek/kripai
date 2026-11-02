# Odbiór po próbach właściciela

Właściciel potwierdził: panel integracji, zatrzymywanie/Gaming i historia działają.
Próba długiej strony zwróciła odpowiedź, ale bez URL/oryginału nie potwierdzamy
zgodności faktów (w tym daty 1966). Nie jest to odbiór wszystkich dużych stron.
README GitHuba zwróciło informacje; lista app była zmieszana z przypuszczeniami.

Naprawa: katalog z Contents API jest teraz listą ścieżek, bez streszczania LLM,
z content_kind=directory. Każdy katalog ma osobny URL /tree/HEAD/path, więc
listy różnych katalogów nie zastępują się w wynikach. Planer dostaje instrukcję
wyboru tree/file; końcowy model ma przytoczyć listę bez zgadywania funkcji plików.
Zajawki wyszukiwarki mają content_kind=search_snippet, odróżnione od odczytu stron.

Rzeczywisty uruchomiony model CUDA na Windows, prawdziwy tokenizer oraz
proces sieciowy: pytanie właściciela o app → section=tree,path=app → lista 17
plików → końcowa odpowiedź wymienia te pliki bez przypuszczeń. 569 tokenów wejścia.
Próba nie zapisuje rozmowy ani nie restartuje prywatnego backendu.
Odtwarzalne polecenie przy uruchomionym modelu: scripts/verify_tool_evidence.py.

Wyszukiwanie pathlib NIE ZALICZONE. Bing RSS poprawnie przyjmuje zapytania,
ale zwraca wyniki niezgodne z nimi (m.in. Python ogólnie, oferty pracy, quizy).
Odtworzono kilkoma zapytaniami i rzeczywistym modelem. To ograniczenie dostawcy,
nie brak oficjalnej dokumentacji. Nie dodano obejść ani pozornego fallbacku.
Kolejny zakres 4b: jawny wybór alternatywnego dostawcy z testem trafności,
konfiguracją lokalną, limitami i widocznym błędem; brak automatycznego eksportu
historii lub nowych zapytań po odczycie niezaufanych wyników.

Obejście do testu samego odczytu: włącz Internet i podaj w bieżącej prośbie
https://docs.python.org/3/library/pathlib.html, prosząc o wyjaśnienie Path.exists().
To test odczytu wskazanego URL, nie test wyszukiwarki.

## Prywatne repo — opcjonalny test właściciela

Publiczny GitHub działa bez tokenu; jeśli nie potrzebujesz prywatnego repo,
punkt 8 można pominąć i oznaczyć jako niewykonany.

1. Na GitHub otwórz Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token. Wybierz właściciela repo,
   krótki termin ważności i Only select repositories. Zaznacz tylko repo do testu.
2. Repository permissions: Contents Read-only. Issues Read-only tylko jeśli
   chcesz czytać issues; Metadata według wymagania GitHuba. Bez Write.
3. Windows / PowerShell, w folderze projektu:

   ```powershell
   powershell -NoProfile -File .\scripts\configure-github.ps1
   ```

4. Wpisz owner/repo. Token wklej wyłącznie do ukrytego lokalnego monitu skryptu.
   Nie wklejaj tokenu do rozmowy, kodu, polecenia ani zrzutu ekranu.
5. W panelu Integracje wpisz to samo owner/repo i uruchom test połączenia.
   Potem włącz GitHub i poproś o strukturę tego repo. Porównaj z GitHubem.
6. Sprawdź inne prywatne repo poza listą: dostęp ma zostać odrzucony.
   Cofnięcie: unieważnij token w GitHub i usuń github.json z folderu danych.

Źródło ustawień tokenu:
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

Po pobraniu poprawek: WYLACZ.cmd, START.cmd, Ctrl+F5. Architektura, modele,
VRAM i baza bez zmian. Test prywatnego konta nadal NIE URUCHOMIONO.

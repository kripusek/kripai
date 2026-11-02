# Przegląd PR tylko do odczytu

03.11.2026. W menu + włącz GitHub. Poproś o listę otwartych PR owner/repo albo
odczyt PR #numer w tym repozytorium. Model może omówić opis i tekstowe patche,
bez publikowania komentarza, akceptacji, merge ani zmiany gałęzi.

github_read: section=pulls listuje 10 ostatnio aktualizowanych otwartych PR;
pobranie 11 pozwala zaznaczyć istnienie dalszych wyników. section=pull oraz
dodatni number czyta konkretny PR, także zamknięty. Zakres repo musi pochodzić
z bieżącej prośby. Nie ma automatycznej paginacji ani zatwierdzania z treści PR.

Przegląd wykonuje trzy GET: metadane → pliki → metadane. Head i base SHA muszą
pozostać identyczne; zmiana odrzuca niejednoznaczny wynik. Źródło przechowuje
SHA odczytu, a link otwiera PR, który w przyszłości może mieć inną wersję.
Diffy nie ustawiają editable i nie dają prawa do propozycji/publikacji zmian.

Limity: do 20 plików (API pyta o 21), 2000 znaków opisu i 6000 znaków patcha
na plik. Liczba plików metadanych nie oznacza pełnego przetworzenia ich kodu;
text_patch_files wskazuje obecne patche. Brak patcha/binary, ucięcie, dalsze
pliki i za duża odpowiedź API dają jawny zakres częściowy. Gdy lista plików
przekracza 512 KiB, pozostają metadane PR z diff_error, nie udawana recenzja.
Lokalne notatki nadal mają budżet 8 fragmentów i tokenizer kontekstu 4096.

Typowe nazwy poświadczeń (.env, klucze PEM/KEY, bazy itp.) nie są przekazywane
jako patch; dotyczy to również poprzedniej nazwy przy rename. Bezpośredni
odczyt takich plików jest zablokowany. Nie jest to pełny skaner sekretów
ukrytych w dowolnym pliku kodu. Poświadczenia samej integracji pozostają
poza repo/wynikiem/modelem, w lokalnym DPAPI; token tylko do api.github.com.

Publiczny GitHub działa anonimowo. Prywatny PR wymaga Pull requests: Read-only
we wskazanym repo. Kreator nowego tokenu proponuje odczyt Contents i PR;
zapis wyłącznie po dotychczasowym jawnym zaznaczeniu dla autoexec. Nie zmieniamy
uprawnień już skonfigurowanego tokenu. Token z samym Contents nadal czyta pliki,
a próba PR może dostać odmowę. Nie wpisuj poświadczeń w rozmowie.

Windows: 213 Python (212 OK, 1 symlink pominięty), Node 55/55. Rzeczywisty
anonimowy proces potwierdził pustą listę PR kripusek/kripai i odczyt zamkniętego
python/cpython #158469: 1 plik, 1 patch, zakres częściowy. Bez tworzenia PR.
Prywatne konto w tym module NIE URUCHOMIONO; autoryzacja transportu testowana
kontrolowanym tokenem. Dosłowny raport: GITHUB_PR_ODCZYT_TESTY.txt.

Kod: app/github_pulls.py, app/network.py, app/tools.py, web/integrations.js,
web/tools.js i testy. Start START.cmd; bez migracji, nowych zależności i API zapisu.
Kontrakt: [GitHub Pull Requests REST](https://docs.github.com/en/rest/pulls/pulls).

Osobno CUDA/Qwen3-8B q8 KV odczytał PR python/cpython #158469 i zakończył
odpowiedź ze źródłem (1106 znaków). Cała karta 7187/8192 MiB po próbie.
To test przepływu i źródła, nie gwarancja trafności każdej recenzji.

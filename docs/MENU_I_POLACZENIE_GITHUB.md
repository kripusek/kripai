# Menu i kreator GitHuba — 02.11.2026

Pole wiadomości ma przycisk „+” obok Wyślij. Zdjęcie, pliki/PDF, pamięć
dokumentów, Internet, GitHub, głos i połączenia są w zamykanym menu. Escape,
klik poza menu oraz wysłanie wiadomości zamykają je. Dostęp do sieci nadal
wymaga jawnego zaznaczenia przełącznika. Wylogowanie czyści wybór i okno konta.
Duży panel integracji przeniesiono do osobnego dialogu „Połączenia”.

## Łączenie bez PowerShella

„+” → „Połącz GitHub / integracje”:

1. Podaj maks. 5 nazw owner/repo. Publiczne repo nadal działa bez logowania.
2. Opcjonalnie zaznacz gałęzie/PR dla kripusek/kripusek-autoexec.
3. „Utwórz ograniczony token w GitHub” otwiera oficjalną stronę GitHuba
   z nazwą, terminem ważności i minimalnymi uprawnieniami. Wybierz tam
   Only select repositories i te same repozytoria co w KripAI.
4. Wklej token wyłącznie w lokalne pole hasła tego okna, nie do rozmowy.
5. „Połącz i sprawdź” testuje konto i wskazane repo przez GET, szyfruje DPAPI
   CurrentUser i atomowo zapisuje konfigurację. Nie trzeba restartować modelu.

To działający kreator tokenu, nie OAuth ani integracja odziedziczona po ChatGPT.
Pełne logowanie OAuth wymaga własnej zarejestrowanej aplikacji GitHub — nie
używamy cudzych client ID ani sekretów. Nie zarejestrowano aplikacji właściciela.

Sekret nie trafia do query URL, rozmów, modelu, localStorage, repo ani logów.
Pole jest czyszczone po wysłaniu, błędzie, zamknięciu i wylogowaniu. Backend
sprawdza owner/sesję/CSRF/Origin/Host; ponownie sprawdza sesję przed zapisem,
gdy test sieci trwał dłużej. Błąd walidacji nie odbija podanego tokenu.

Nieudany test lub szyfrowanie pozostawia poprzednie połączenie. Zmiana i lokalne
odłączenie najpierw zapisują kopię istniejącej konfiguracji w prywatnym folderze
kopii /credentials. Kopie zawierają zaszyfrowany token. Odłączenie nie unieważnia
PAT w GitHub; odwołaj go również w ustawieniach GitHuba. Potwierdzenie write
pozostaje ograniczone do autoexec, nie daje modelowi dowolnego zapisu.
Nie podłączono ani nie zmieniono rzeczywistego konta właściciela w testach.

## Weryfikacja

Prawdziwy Chrome headless, izolowany profil i lokalny serwer z kontrolowanym API:
zamknięte/otwarte menu, okno połączenia, desktop i 390×844. Menu mieści się
w ekranie (left 131, right 371 przy szerokości 390), pole wiadomości nie ma
stałego paska opcji. To wizualny test UI, nie test realnego konta.
Zrzuty są lokalnie w reports/composer-closed.png, composer-open.png,
composer-mobile.png i github-connect.png. Nie zawierają prywatnych danych.

Testy obejmują prawdziwy Windows DPAPI ze sztucznym tokenem, zachowanie starej
konfiguracji po awarii, kopię przed odłączeniem, brak zapisu po wylogowaniu,
sesję/CSRF i brak sekretu w odpowiedzi. Dosłowne wyniki: WINDOWS_MENU_TESTY.txt.
Nowe pliki: app/github_connect.py, web/composer-menu.js i testy kreatora/menu.
Bez nowych bibliotek, zmiany modelu, schematu rozmów ani obciążenia VRAM.

Start: WYLACZ.cmd → START.cmd → Ctrl+F5.

Źródła:
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

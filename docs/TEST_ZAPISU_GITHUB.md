# Rzeczywista próba gałęzi i PR — 02.11.2026

Właściciel jawnie zezwolił na testy zapisu tylko w kripusek/kripusek-autoexec.
Nie obejmuje to merge, zmiany main ani innych repozytoriów.

Nie powielano ani nie zapisywano klucza podanego w rozmowie. Zalecono jego
unieważnienie i zastąpienie nowym tokenem w lokalnym kreatorze. Test korzystał
z istniejącego zaszyfrowanego poświadczenia w folderze danych, bez jego eksportu.
Lokalne ustawienie uprawnień działającego modelu nie zostało zmienione;
zgoda testowa była ograniczona do osobnego procesu i jednego repozytorium.

Przygotowano czytelniejszy README: lista kroków instalacji, komendy w blokach
kodu, tabela istniejących klawiszy, opisy obrazków i zachowane autorstwo.
Sprawdzono zachowanie obu oryginalnych adresów grafik i komend.
Nie zmieniano konfiguracji gry ani nie deklarowano uruchomienia gry.

Rzeczywiste odczyty konta/repo i utworzenie lokalnego diffu przeszły. GitHub
odrzucił pierwszą mutację POST git/trees. Nie powstała gałąź ani PR; odczytowe
sprawdzenie nie znalazło gałęzi testowej. Nie ponawiano mutacji automatycznie.
Próba zakończonej publikacji NIE ZALICZONA — potrzebne lokalnie skonfigurowane
poświadczenie z Contents i Pull requests: write dla wskazanego repozytorium.
Nie używamy logowania agenta do KripAI jako uprawnienia lokalnego modelu.

## Poprawiona obsługa odmowy

401 daje czytelny błąd poświadczenia, 403 przy zapisie błąd uprawnień, a 429
lub sygnał limitu w nagłówkach błąd limitu. Treść zdalnego błędu ani token nie
trafia do wyjątku/logu/modelu. Jednoznaczna odmowa 4xx przed pierwszą udaną
mutacją zachowuje propozycję jako prepared. Po poprawieniu konfiguracji owner
może ręcznie ponowić tę samą propozycję. Nie ma automatycznych ponowień.
Po udanej mutacji albo utracie odpowiedzi stan nadal jest outcome_unknown
i wymaga odczytowego uzgodnienia, zamiast ślepego powtórzenia POST.
Historyczna próba sprzed poprawki pozostaje niepewna w oddzielnym dzienniku;
nie zmieniano jej stanu na podstawie przypuszczeń.

Testy: prawdziwy SQLite, kontrolowane statusy HTTP, brak echo sekretów,
brak automatycznego retry, zachowanie propozycji i późniejszy ręczny retry,
odmowa po pierwszej mutacji pozostająca niepewna. To regresja protokołu,
nie potwierdzenie prawdziwego PR. Start nadal START.cmd; bez nowych zależności.

Źródło kontraktu:
https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api

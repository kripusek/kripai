# KripAI — Windows, bez WSL i Dockera

## Poprawka ucinania odpowiedzi — 02.11.2026

Windows: rozpakuj aktualną paczkę do osobnego folderu → START.cmd → Ctrl+F5.
Nie są potrzebne nowe modele. Limit generowania tekstu/obrazu podniesiono
z 768 do 2048 tokenów; kontekst modelu nadal 4096, więc rezerwacja wyjścia
zmniejsza miejsce na poprzednie tury w kontekście, nie usuwa zapisanej historii.
Jeżeli model zakończy przez limit, panel pokaże „Odpowiedź jest niepełna”.
Pod odpowiedzią dostępny jest przycisk Kontynuuj: wstawia prośbę z końcowym
fragmentem do edycji; trzeba kliknąć Wyślij. To nowa odpowiedź, nie gwarancja
bezszwowego scalenia kodu. Może wymagać zachowania obu fragmentów i korekty.

Sprawdzenie Windows/przeglądarka: poproś o długi przykład kodu. Odpowiedź powinna
mieć większy budżet; po dojściu do limitu ma pojawić się ostrzeżenie. Kliknij
Kontynuuj: końcówka poprzedniej odpowiedzi ma pojawić się w polu, bez wysłania.
Krótka odpowiedź zakończona normalnie nie powinna wyświetlać ostrzeżenia.
Długie pojedyncze pytanie może wymagać skrócenia, aby zmieścić się w kontekście.
Błąd połączenia jest nadal błędem, nie poprawnym zakończeniem odpowiedzi.


## Zdjęcia w czacie i formatowanie — aktualizacja 02.11.2026

**Windows:** rozpakuj całą nową paczkę do osobnego folderu, uruchom **START.cmd**,
po otwarciu panelu naciśnij **Ctrl+F5**. Hasło i historia pozostają; przed migracją
bazy powstaje kopia. Bez nowego modelu: używany jest poprzedni Qwen3-VL,
który START pobierze tylko jeśli jeszcze nie został przygotowany.

Sprawdź w przeglądarce Windows:
1. Kliknij pole wiadomości → Ctrl+V z obrazem w schowku. Powinna pojawić się
   miniatura, bez automatycznego wysłania. Alternatywy: przeciągnij plik na
   formularz lub kliknij **＋ Zdjęcie**.
2. Dopisz pytanie → **Wyślij**. Zdjęcie powinno zostać w historii, a odpowiedź
   pojawiać się pod nim stopniowo. Bez pytania używane jest „Opisz to zdjęcie.”.
3. Zmień rozmowę i wróć — obraz i odpowiedź powinny pozostać. Nie wysłana
   miniatura jest czyszczona po zmianie rozmowy i wylogowaniu.
4. Poproś o przykład HTML w bloku kodu, nagłówek i listę. Blok powinien mieć
   etykietę języka i **Kopiuj**. Wklej do Notatnika — sam kod bez znaczników bloku.
5. Sprawdź podstawowe wzory: `$x^2$`, `$\frac{1}{2}$`, `$(-\infty,2]$`.
   Nagłówki, pogrubienia, listy, cytaty i tabele powinny być sformatowane również
   w starszych odpowiedziach, a nie wyświetlać samych znaczników.
6. Podczas uploadu lub odpowiedzi kliknij **Zatrzymaj**. Wyloguj się — późne
   wyniki nie powinny wracać do panelu.

Ograniczenia: jedno PNG/JPEG do 8 MiB na wiadomość; PDF nadal w osobnym panelu.
Pytanie do VLM używa bieżącego zdjęcia i pytania. Następna zwykła wiadomość
korzysta z tekstu historii, nie ponownie z pikseli: do dalszej analizy zdjęcia
załącz je ponownie. Nie ma jeszcze pełnej pamięci multimodalnej ani RAG.
Podstawowy MathML nie jest pełnym LaTeX — nieznane komendy/środowiska zostają
jako źródło. Bloki kodu bez kolorowania składni. HTML/JS odpowiedzi nie wykonuje się.

Usunięcie pliku w Zdjęcia i PDF usuwa jego podgląd z historii po odświeżeniu;
stare kopie mogą go zachować. Anulowany upload może zostawić plik w tym panelu
(do ręcznego usunięcia). Nie jest to bezpieczne wymazanie dysku.

---

**Windows 11 x64:** rozpakuj cały ZIP i kliknij **START.cmd**.
Nie przenoś samego START.cmd. Instalator przygotuje prywatny Python, biblioteki,
llama-server CUDA i model, poprosi o własne hasło i otworzy **http://localhost:8765**.
Login: **owner**. Pierwszy start pobiera około 5 GB modelu i około 650 MB binariów.
Moduł głosu pobiera dodatkowo około 497 MB (silnik CPU + model).
Obrazy: dodatkowe około 3.34 GB modelu Qwen3-VL.
Potrzebny sterownik NVIDIA i co najmniej 16 GB wolnego miejsca. Żadnych kont chmurowych.
Windows może poprosić o zgodę na oficjalny runtime Microsoft Visual C++, jeśli go brakuje.

**WYLACZ.cmd** zamyka backend i jego model. Zamknięcie karty przeglądarki ich nie zamyka.
Przed grą kliknij **Włącz Gaming** w panelu. Po grze **Wróć do rozmów**.
Oczekuj kolejno „model wyłączony” i „model gotowy”. Nie edytujesz żadnych plików.

## Co jest zachowane i poprawione
Logowanie, sesje, historia, odpowiedzi na żywo (SSE), anulowanie, idempotencja
oraz Gaming. Historia pozostaje w bazie, panel ładuje po 50 wiadomości.
Model dostaje ostatnie pełne tury dopasowane tokenizerem do 4096 tokenów;
panel informuje o pominięciu starszych wiadomości. To nie nieograniczona pamięć.

## Twoja dotychczasowa historia
Nowa instalacja używa nowej bazy SQLite. Stara baza WSL pozostaje nietknięta.
Aby skopiować rozmowy: po pierwszym uruchomieniu nowej wersji kliknij w Windows
**IMPORT_HISTORII.cmd**, gdy stary panel https://localhost:8443 jeszcze działa.
Podaj hasło starego owner; import zachowuje ID, treść i czas wiadomości, nie
przenosi sesji, sekretów ani zadań. Ponowienie nie duplikuje rozmów. Potem
uruchom START.cmd. Nowa aplikacja nie potrzebuje już starego panelu ani WSL/Dockera.
Nie usuwaj starej bazy przed sprawdzeniem importu. Import nie przenosi modelu:
nowa instalacja pobiera własny plik GGUF z kontrolą SHA-256.

## Przydatne przyciski — pliki uruchamiane w Windows

| Plik | Działanie |
|---|---|
| START.cmd | Instalacja, aktualizacja lub start i otwarcie strony |
| WYLACZ.cmd | Zamyka wyłącznie KripAI i uruchomiony przez nie model |
| BACKUP.cmd | Tworzy sprawdzoną kopię także podczas pracy |
| PRZYWROC_KOPIE.cmd | Zamyka aplikację, pozwala wybrać kopię, wcześniej zabezpiecza aktualny stan |
| RESET_HASLA.cmd | Zamyka aplikację, robi kopię, ustawia nowe hasło i unieważnia sesje |
| ODINSTALUJ.cmd | Usuwa program po potwierdzeniu; dane zostają domyślnie |
| TESTY.cmd | Testuje na tymczasowych danych, bez używania Twoich rozmów ani modelu |
| IMPORT_HISTORII.cmd | Jednorazowe kopiowanie rozmów ze starego panelu |

Program: `%LOCALAPPDATA%\KripAI`. Dane/model: `%LOCALAPPDATA%\KripAI-data`.
Kopie: `%LOCALAPPDATA%\KripAI-backups` — 14 ostatnich. Kopie są wykonywane też
przy starcie, zamknięciu i co 24 godziny pracy. Nie zawierają dużego modelu.
Skopiuj wybrany gotowy plik .sqlite3 na drugi nośnik, jeśli chcesz zabezpieczyć
się przed awarią dysku. Kopie zawierają prywatną historię i nie są szyfrowane.

## Krótki test po instalacji
1. Zaloguj się, poczekaj na gotowość modelu, zadaj pytanie. Tekst ma pojawiać się
   stopniowo. Odśwież stronę — rozmowa powinna pozostać.
2. Kliknij Gaming podczas odpowiedzi. Odpowiedź ma się przerwać, stan zmienić
   na „model wyłączony”, a proces llama-server KripAI zniknąć w Menedżerze zadań.
   Wróć do rozmów i zadaj kolejne pytanie.
3. Windows: WYLACZ.cmd, potem START.cmd. Historia ma pozostać.
4. Windows: BACKUP.cmd. Zapisz nową rozmowę, użyj PRZYWROC_KOPIE.cmd i wybierz
   wcześniejszą kopię. Po START zobaczysz stan z tej kopii; nowszy stan ma osobny backup.
5. Windows: RESET_HASLA.cmd, potem START.cmd. Stare hasło i stare sesje mają nie działać.
6. Po ponad 50 wiadomościach użyj „Starsze wiadomości”. Historia nie może mieć duplikatów.
7. Opcjonalny test odinstalowania: ODINSTALUJ.cmd → TAK → Enter przy pytaniu o dane.
   Ponowny START ma zachować historię, model i hasło. Nie wpisuj USUN DANE podczas tego testu.

## Gdy coś nie rusza
- „CUDA niedostępna”: zaktualizuj sterownik NVIDIA w Windows. Nie instaluj WSL ani CUDA Toolkit.
- „Model się ładuje”, potem błąd: zamknij grę/programy zajmujące VRAM i ponów tryb rozmów.
- Przerwany download: uruchom START ponownie; plik .part jest wznawiany i sprawdzany.
- Błąd testu: raport `%LOCALAPPDATA%\KripAI\reports\tests-latest.txt`.
- Port 8765 zajęty: nie kończymy obcego programu; zamknij go albo zgłoś konflikt.
- Po aktualizacji odśwież stronę Ctrl+F5. START aktualizuje program, nie usuwa danych.

## Granice i stan
HTTP działa tylko lokalnie. Nie wystawiaj tego portu przez tunel ani router.
Natywnego instalatora Windows, rzeczywistego CUDA i pomiaru VRAM nie uruchomiono
w środowisku przygotowania (Linux). Dokładny raport: docs/WYNIKI_TESTOW.txt.
Testy aplikacji używają prawdziwego SQLite i kontrolowanego serwera HTTP zamiast
modelu; testy procesów rzeczywiście uruchamiają i kończą procesy potomne.
Plan i stan etapów 2–6 są w spec/06-rollout.md; RAG na sqlite-vec nie jest jeszcze wdrożony.

## Nowość: głos — wstępny etap 2
Aktualizacja w Windows: rozpakuj nową paczkę i kliknij START.cmd, następnie
Ctrl+F5 w panelu. Historia i hasło zostają. Nie trzeba instalować Pythona
ani edytować konfiguracji. Pierwsze pobranie modeli wymaga internetu; później
rozpoznawanie i odczyt działają lokalnie.

1. Wybierz **Polski** lub **English**, kliknij **Nagraj** i zezwól na mikrofon.
   Powiedz krótkie zdanie, kliknij **Zakończ nagranie**. Limit: 30 sekund.
2. Oczekuj tekstu w polu wiadomości — popraw go i dopiero kliknij **Wyślij**.
   Głos sam nie wysyła wiadomości, nie wykonuje poleceń i nie zapisuje audio.
3. Pod odpowiedzią kliknij **Czytaj**. Oczekuj lokalnego odczytu całej odpowiedzi
   (do 12 000 znaków, w kolejnych porcjach). **Zatrzymaj głos** przerywa odczyt.
4. Podczas nagrywania/rozpoznawania kliknij **Zatrzymaj głos**: mikrofon gaśnie,
   wynik nie dopisuje tekstu. Gaming i wylogowanie też przerywają głos.
5. Sprawdź odmowę dostępu i odłączenie mikrofonu — oczekiwany czytelny komunikat.
   Powtórz próbę PL i EN, także po wyłączeniu internetu.

Odczyt używa dostępnych lokalnych głosów Windows **System.Speech**. Jeżeli
brakuje głosu wybranego języka, zobaczysz błąd — nie ma zamiennika w chmurze.
Nie wszystkie głosy Narratora/OneCore są widoczne dla System.Speech; aplikacja
nie zmienia rejestru. To ograniczenie wstępnej wersji, do sprawdzenia na Windows.
Nagrywanie kończy się też przy schowaniu karty. WYLACZ zamyka procesy; panel
wykrywa utratę backendu lub Gaming z drugiej karty w swoim cyklu kontroli (3 s).

**Potwierdzono:** API/SQLite, anulowanie prawdziwych procesów, logikę nagrywania
i odtwarzania w testach JS oraz rzeczywiste Whisper CPU EN na Linux.
**NIE URUCHOMIONO:** mikrofon/przeglądarka i System.Speech na Windows, jakość
PL/EN na Twoim sprzęcie, pomiar opóźnień i instalacja Windows. Etap 2 nie jest
jeszcze uznany za odebrany. Dosłowne wyniki: docs/WYNIKI_TESTOW.txt.

### Poprawka rozpoznawania polskiego
Po zgłoszeniu błędów w dyktowaniu zastąpiono Whisper base modelem small
wielojęzycznym. Aktualizacja: nowa paczka → START.cmd w Windows → Ctrl+F5.
Pobierany jest nowy model około 488 MB. Stary plik base nie jest używany
ani automatycznie usuwany. Small może działać wolniej na CPU; jakość konkretnego
zdania trzeba porównać na tym samym nagraniu. Nie dodano automatycznych zamian
słów ani poprawiania transkrypcji modelem czatu. Wybierz Polski przy polskim
zdaniu zawierającym nazwy HTML/CSS/JavaScript. Wynik nadal sprawdzasz przed wysłaniem.

## Aktualizacja: zdjęcia i PDF — etap 2.5a

**Windows:** rozpakuj nową paczkę do osobnego folderu i uruchom `START.cmd`.
Zatrzyma poprzednią instancję, zaktualizuje program i wykona kopię przed migracją
istniejącej bazy. Hasło i historia zostają. Pierwsze przygotowanie modelu obrazu
pobiera dodatkowe około **3.34 GB**; zapewnij łącznie co najmniej 16 GB wolnego
miejsca na program i modele. Pobieranie pokazuje postęp. Błąd pobrania VLM nie
blokuje czatu i podglądu plików; następny START ponawia pobranie.
W przeglądarce pod http://localhost:8765 naciśnij **Ctrl+F5**.

### Sprawdzenie ręczne (Windows / przeglądarka)
1. Zaloguj się; poprzednie rozmowy powinny nadal być widoczne.
2. Kliknij **Zdjęcia i PDF**, dodaj PNG/JPEG z czytelnym napisem. Powinien
   pojawić się podgląd. Kliknij **Odczytaj tekst** i porównaj wynik z obrazem.
3. Dodaj dwustronicowy PDF z tekstem. Zmień stronę na 2 → **Pokaż stronę**.
   Podgląd i tekst powinny odpowiadać drugiej stronie. Skany wymagają VLM.
4. Zadaj pytanie o obraz. Czat chwilowo niedostępny podczas zamiany modelu;
   po zakończeniu model tekstowy wraca. OCR może się mylić — sprawdź wynik.
5. Kliknij **Wstaw do wiadomości**. Tekst ma trafić do pola edycji, bez
   automatycznej odpowiedzi. Dodaj pytanie i dopiero wtedy kliknij Wyślij.
6. Podczas analizy kliknij **Anuluj**, potem sprawdź powrót do czatu.
   Włącz Gaming w panelu trybu: proces llama-server powinien zniknąć z
   Menedżera zadań. To również miejsce na pomiar faktycznie zwolnionego VRAM.
7. `BACKUP.cmd` (Windows) tworzy kopię obejmującą rozmowy i pliki.
   Usuń testowy plik: powinien zniknąć z listy; kopia zachowuje poprzednie dane.
   Przywracanie sprawdzaj na danych testowych — przywraca cały stan, nie jeden plik.
8. `WYLACZ.cmd` (Windows), potem START: historia i załączniki mają pozostać.

Limity: 8 MiB/plik, 50 stron PDF, pojedyncza strona do analizy, 50 plików,
200 MiB razem z podglądami, 12000 znaków wyniku. Pole wiadomości nadal ma
4000 znaków — z długiego wyniku wybierz fragment. Nie ma jeszcze RAG.
Przed usuwaniem tworzona jest kopia; dane mogą pozostać w starszych kopiach.
Nie jest to mechanizm bezpiecznego wymazania dysku. Dekoder ma limit pamięci
512 MiB i czasu 20 s, ale Windows Job Object nie jest pełnym sandboxem.
Testy CUDA/VRAM i wizualny odbiór Windows pozostają do wykonania na docelowym PC.

## Nowy moduł 2.5b — pamięć tekstowych PDF
Windows: zaktualizuj źródła (git pull --ff-only), uruchom START.cmd i Ctrl+F5.
START pobiera dodatkowy model E5 około 126 MiB oraz sqlite-vec. Rozmowy zostają.
Dodaj tekstowy PDF w „Zdjęcia i PDF”, otwórz „Pamięć dokumentów”, kliknij Indeksuj.
Po stanie Gotowy zaznacz dokument i zadaj pytanie w czacie. Oczekuj nazw, stron
i wycinków źródeł pod odpowiedzią. Sprawdź Wstrzymaj/Wznów, restart i Gaming.
Skany i strony >12000 znaków są jawnie odrzucane; nie są gotowym indeksem.
Usuń indeks zachowuje PDF, Usuń plik usuwa też indeks; wycinki znikają z replay.
Sprawdź backup/restore źródeł i wektorów na danych testowych, bez kasowania
prywatnej bazy. Zmierz RAM/VRAM — Linux QA nie potwierdza tych wyników Windows.

## Internet/publiczny GitHub — pierwszy moduł 4a
Windows: git pull --ff-only, START.cmd, Ctrl+F5. Nowa migracja ma kopię przed zmianą.
Przełączniki pod czatem są początkowo wyłączone. Włącz Publiczny GitHub, wpisz
„Przeczytaj README kripusek/kripai i streść go”. Oczekuj stanu odczytu i [W1].
Dla WWW włącz Internet i podaj konkretny URL HTTPS. Odczyt do 1200 znaków,
bez JavaScript; większa strona może być częściowym źródłem lub zostać odrzucona.
Sprawdź offline/Cancel/Gaming/wylogowanie, odmowę localhost i błędnego serwera.
Prywatne repo, zapis i ogólne wyszukiwanie WWW jeszcze niedostępne.
Jeżeli brak źródła, panel nie potwierdza, że odpowiedź ma aktualne dane z internetu.
Natywny odbiór modelu z narzędziami, sieci i UI nie został wykonany w QA.

## Większe strony i wyszukiwanie 4b
Po git pull --ff-only uruchom START.cmd i Ctrl+F5. Włącz „Internet: szukaj i czytaj”.
Możesz wpisać pytanie bez URL; Bing RSS dostarczy wyniki, a model może je odczytać.
Dłuższa strona przechodzi przez ekstrakcję i lokalne notatki; to może potrwać
więcej niż pojedyncza odpowiedź. Panel pokazuje stan streszczania.
Przy limicie używany jest częściowy tekst, nie odrzucana całość. Sprawdź źródła.
Nie obiecuje to stron z logowaniem/CAPTCHA/JS ani dostępności każdego serwisu.
Wyszukiwarka to publiczny kanał RSS z limitami operatora, nie usługa z gwarancją SLA.

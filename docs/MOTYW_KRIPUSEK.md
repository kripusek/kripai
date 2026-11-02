# Motyw kripusek i domknięcie site:

Czerń #0c0c0f, grafitowe panele, czerwień #dc263d, jasny tekst i widoczny
focus klawiatury. Logowanie, rozmowa, menu + i integracje mają spójną paletę.
Nowy web/theme.css zachowuje bazowy układ i funkcje. Favicon dopasowany.
Wszystko jest lokalne; Inter używany tylko, jeśli już jest zainstalowany,
w pozostałych przypadkach Segoe UI/systemowy. Bez zewnętrznych czcionek/grafik.

Sprawdzono publiczne źródła właściciela:
https://github.com/kripusek
https://github.com/kripusek/stardance-personal-site
https://raw.githubusercontent.com/kripusek/stardance-personal-site/main/style.css
Stara strona jest wielokolorowa; czarno-czerwona paleta to aktualne polecenie.
kripusek.top było niedostępne w narzędziu WWW; nie udajemy jego obejrzenia.

Przegląd Chrome: desktop i 390 px, logowanie, menu +, dialog połączeń,
wiadomość. Pomiar scrollWidth nie wykazał poziomego overflow. Zrzuty w
reports/kripai-dark-*.png są lokalnymi artefaktami QA, bez danych właściciela.
API podglądu było kontrolowane. Nie jest to zaliczenie logowania hasłem owner.

Przekierowania wyników site: są sprawdzane przed każdym DNS/połączeniem.
Zakres pochodzi z wiadomości/query wyszukiwania, przekazany przez backend.
Wynik nie może przekierować na obcy host ani wykluczoną poddomenę.
Jawny URL właściciela pozostaje osobno autoryzowany. Testy transportu używają
kontrolowanych HTTP, a rzeczywistych procesów narzędzia nie zastępują atrapą.

Pełny raport: MOTYW_TESTY.txt. Start nadal START.cmd, schemat 6 bez migracji.
Po aktualizacji odśwież stronę Ctrl+F5. Dane i pliki programu skopiowano przed
aktualizacją; backend i model CUDA ponownie osiągnęły gotowość. Jedna próba
rzeczywistego inference przed wznowieniem modelu zakończyła się przerwaniem;
nie uznano jej za test zaliczony. Przyczyną znikania backendu po poleceniach agenta był odziedziczony Windows Job.
Launcher odłącza backend, gdy nadrzędny Job na to pozwala; przy odmowie
Windows zachowuje zwykły start. Limity i zamykanie modeli/narzędzi nadal działają.
Pozostałe szczegóły: najnowszy wpis PROJECT_STATE.md.

Zwykłe zainstalowane manage.py stop/start przeszło po kopii kodu i danych.
W osobnym kolejnym poleceniu health/live oraz chronione v1/models dały 200;
backend i model przeżyły zakończenie launchera. Nie trzeba skryptu pomocniczego.

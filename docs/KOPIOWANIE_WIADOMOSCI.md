# Kopiowanie całej wiadomości

Pod wiadomością użytkownika i asystenta jest **Kopiuj całą wiadomość**.
Przycisk kopiuje oryginalny pełny tekst, z zapisem Markdown i znacznikami źródeł
takimi jak [W1]. Nie kopiuje obrazu, binariów załączników ani dodatkowych
wycinków panelu źródeł. Kod Markdown pozostaje gotowy do wklejenia w edytorze.
Przycisk Kopiuj przy pojedynczym bloku kodu działa nadal niezależnie.
Systemowy schowek Windows może normalizować końce linii LF do CRLF;
nie oznacza to utraty tekstu.

Kopiowanie następuje wyłącznie po kliknięciu przez lokalne API schowka
przeglądarki. Nie wysyła żądań do serwera, modelu ani usług zewnętrznych.
Podczas generowania kopiuje tekst otrzymany do chwili kliknięcia; późniejsze
fragmenty nie zmieniają już schowka. Tekst pobieramy z bieżącego źródła, a nie
ze sformatowanego HTML. Duży tekst i Unicode nie są skracane przez aplikację.

Odmowa dostępu i brak API mają czytelny komunikat; nie deklarujemy sukcesu.
Można zezwolić przeglądarce na schowek lub zaznaczyć i skopiować tekst ręcznie.
Pusta odpowiedź nie nadpisuje schowka. Oczekujące kopiowanie blokuje następne
kliknięcia, zachowując fokus przycisku. Nie zmieniamy niewysłanego tekstu ani
załącznika szkicu. Nie używamy przestarzałego execCommand.

Wylogowanie oraz przeładowanie kontekstu rozmowy unieważnia stare przyciski
i spóźnione komunikaty operacji. Już zleconego systemowi zapisu schowka nie
można cofnąć; wylogowanie nie czyści systemowego schowka.

Implementacja: web/message-copy.js, bubble/load/showLogin w web/app.js.
Brak migracji, bibliotek i dodatkowych uprawnień modelu. Start START.cmd,
następnie Ctrl+F5 w otwartej wcześniej przeglądarce.

Windows: 302 testy Python (301 zaliczonych, 1 pominięty), 145/145 Node.
Rzeczywisty Chromium sprawdza lokalny schowek, oba rodzaje wiadomości,
Markdown/Unicode, odmowę dostępu, zachowany szkic/fokus i późną obietnicę
po logout. Próby na izolowanym rzeczywistym API, bez inferencji GPU.
Dosłowny raport: KOPIOWANIE_WIADOMOSCI_TESTY.txt.

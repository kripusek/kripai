# Filtr domen w wyszukiwaniu WWW

02.11.2026. Włącz Internet pod + i podaj operator z samą domeną, np.
`Znajdź dokumentację pathlib site:docs.python.org`.
`-site:example.org` wyklucza domenę i jej poddomeny.

KripAI sam sprawdza domeny otrzymanych wyników. Bing RSS potrafi zignorować
site: i zwrócić obce strony; takie wyniki są odrzucane. Dopuszczamy dokładny
host i jego poddomeny: example.org pasuje do docs.example.org, ale nie do
notexample.org ani example.org.evil.test. Obsługiwana jest normalizacja IDNA
i wielkości liter. Nie jest to filtr ścieżek, pełny parser języka zapytań
wyszukiwarki ani obejście blokad serwisów.

Ograniczenia z bieżącej wiadomości właściciela obowiązują również wtedy, gdy
model pominie je we własnym zapytaniu. Model może dodatkowo zawęzić zakres.
Wiele dodatnich operatorów wymaga spełnienia każdego z nich (przecięcie),
wykluczenie ma pierwszeństwo. Sprzeczny zakres daje pustą listę. Operatorów
nie pobieramy ze stron ani historii rozmowy; nie nadają praw zapisu.

Oficjalny indeks Pythona też respektuje filtr: przy site:example.org nie
jest używany jako zastępstwo wskazanej domeny. Filtry nie mają wpływu na
osobno wskazane do odczytu URL; nadal wymagają one istniejącej zgody i kontroli.

Po site: wpisz samą domenę. Ścieżka, schemat URL, port, dane logowania,
parametry, fragment i localhost powodują czytelny błąd przed połączeniem.
Pusta lista oznacza brak pasujących wyników zwróconych przez dostawcę;
nie dowodzi, że żadna strona na świecie nie zawiera odpowiedzi. Planer
otrzymuje informację site_filter z liczbą odrzuconych wyników.

Rzeczywista próba Windows: oficjalny pathlib znaleziony przy
site:docs.python.org. Dla zakresu example.org, przy zapytaniu modelu bez
operatora, Bing zwrócił 10 obcych wyników; wszystkie odrzucono. Testy obejmują
granice DNS, poddomeny/wykluczenia, IDNA, błędne filtry, nadrzędny zakres
wiadomości oraz odmowę użycia indeksu Pythona poza dozwoloną domeną.
Pełne wyniki: SITE_FILTER_TESTY.txt.

Kod: app/network.py, app/tools.py, web/tools.js. Bez migracji i nowych
bibliotek. Start nadal START.cmd. Ogólna jakość wyników Bing i zewnętrzni
dostawcy MCP pozostają dalszymi zakresami. Ta zmiana nie zalicza mikrofonu,
instalatora ani obsługi wszystkich stron.

Osobny rzeczywisty CUDA/Qwen3-8B wykonał wyszukiwanie z site:docs.python.org,
odczytał pathlib i zakończył odpowiedź ze źródłem (614 znaków). Cała karta
7575/8192 MiB VRAM; kontekst nadal 4096.

Aktualizacja zastosowana lokalnie po kopii danych/programu i kontroli braku
aktywnego generowania. Backend i rzeczywisty model ponownie gotowe.
Zainstalowana kopia: oficjalny wynik poprawny, 10 obcych wyników odrzuconych
przy zakresie example.org, health/live 200. Bieżący schemat 6 bez migracji.

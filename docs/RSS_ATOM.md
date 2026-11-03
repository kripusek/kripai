# RSS i Atom: odczyt publicznych kanałów

W **+ → Połączenia → Kanały RSS / Atom** wpisz publiczny adres HTTPS i kliknij
**Test i odczyt kanału**. To rzeczywiste pobranie do pięciu wpisów z bieżącego
kanału, bez konta, modelu i zakładania subskrypcji. Samo otwarcie panelu nie
wykonuje pobrania. URL nie jest zapisywany jako konfiguracja ani w localStorage.

Panel pokazuje tytuł, datę i krótki opis każdego wpisu oraz link do źródła.
**Dodaj pytanie o kanał** albo **Zapytaj o artykuł** dopisuje pytanie do szkicu,
włącza dotychczasową zgodę Internet i przenosi fokus do wiadomości. Wysyłasz
ją osobno. Inne zgody pozostają bez zmian. Niewysłany szkic nie jest usuwany;
przy zdjęciu prosimy o jego odłączenie zamiast usuwać je automatycznie.

W rozmowie możesz włączyć Internet i napisać np. „Odczytaj kanał RSS
https://www.djangoproject.com/rss/weblog/ i podaj dwa pierwsze tytuły”.
Narzędzie `feed_read` wymaga URL w aktualnej prośbie albo w rzeczywiście
uzyskanych wynikach. Wpisy z odczytanego kanału mogą być następnie odczytane
istniejącym web_read; tekst kanału nie nadaje zgody na GitHuba, MCP ani zapis.
Same zajawki nie oznaczają, że artykuły zostały przeczytane.

## Obsługiwany zakres

RSS 2.0 i Atom 1.0 w UTF-8 (także ASCII), do 512 KiB odpowiedzi XML.
Obsługiwany jest namespace Atom, link alternate, względne adresy i xml:base.
Nie pobieramy enclosures, obrazów ani content src; opisy są zwykłym tekstem.
Pokazujemy do 5 prawidłowych, różnych linków, sprawdzając do 20 pierwszych
wpisów. Tytuł do200, data do80, opis do300 znaków; tekst razem do12000.
`provided_entries` dotyczy wyłącznie aktualnego dokumentu kanału. Kolejność
jest kolejnością wydawcy — nie gwarantujemy chronologicznego sortowania.
Puste pole daty pozostaje puste; dat wydawcy nie weryfikujemy niezależnie.

`truncated`, `omitted_entries` i `scope_note` opisują ograniczenia. Brak
prawidłowych wpisów w porcji nie oznacza pustego archiwum serwisu.
Nie obsługujemy RSS1/RDF, innych kodowań, kanałów wymagających konta ani
automatycznego odświeżania w tle. Kanał pod błędnym URL, z odmową serwisu,
nieprawidłowym XML albo zbyt dużą odpowiedzią daje błąd, nie fałszywą pustą listę.

## Granice i bezpieczeństwo

Adapter korzysta z istniejącego ograniczonego procesu odczytu sieci: publiczny
HTTPS GET, kontrola DNS/IP/redirect, TLS, brak cookies/tokenów/proxy, timeout
i anulowanie. Linki plikowe, lokalne IP i dane logowania w URL są odrzucane.
XML nie może zawierać DOCTYPE/ENTITY; limit to20poziomów/5000elementów.
Treść HTML jest zamieniana na tekst; nie wykonujemy skryptów ani instrukcji
z kanału. Model nie zmienia konfiguracji i nie uzyskuje uprawnień zapisu.

Test połączenia wymaga zalogowania i CSRF; sesja jest ponownie sprawdzana
podczas pracy procesu. Wylogowanie i edycja URL unieważniają stare wyniki UI.
To adapter RSS we wspólnym rejestrze, nie kolejny serwer MCP ani integracja
z kontem. Dostawca MCP pozostaje osobnym kolejnym zakresem etapu4c.

## Weryfikacja

Windows:326 Python (325 zaliczonych,1 pominięty symlink), Node154/154.
Nowe testy: RSS/Atom, XMLbase, HTML/skrypty, brak content src fetch, limity,
encje/kodowania, ACL, przejście do artykułu, sesja/CSRF, szkic i późne wyniki.
Stary test schematów używał budżetu końcowej odpowiedzi zamiast planera;
dopasowano go do faktycznego budżetu planera512, bez zmiany kontekstu GPU.

Rzeczywiste procesy bez konta odczytały RSS bloga Django i Atom wydań CPythona,
po5 z10wpisów. Chromium z izolowanym rzeczywistym API: pięć wpisów, szkic/fokus,
Internet bez autosend, mobile390 bez overflow; jawny błąd XML i odpowiedź200
wstrzymana do logout nie odtwarzają danych. Wymuszone awarie były fixture.
Prawdziwy llama-server CUDA wybrał feed_read i zakończył odpowiedź345znaków
z zapisanym źródłem. Konto/kontroler testowe, inferencja rzeczywista;
VRAM całej karty6968/8192MiB po odpowiedzi — pojedynczy pomiar, nie benchmark.
Nie wykonywano nowego testu mikrofonu ani kont prywatnych.
Dosłowny raport: RSS_ATOM_TESTY.txt. Kod feeds.py/integrations/tools/context,
endpoint POST /integrations/feeds/test i web/feeds.js. Brak migracji/deps.
START.cmd, następnie Ctrl+F5.

Kontrakty: [RSS2](https://www.rssboard.org/rss-specification),
[Atom1](https://www.rfc-editor.org/rfc/rfc4287.html).

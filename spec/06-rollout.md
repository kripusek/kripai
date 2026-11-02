# 06 — Plan etapów Windows native
Etap 2 ma wstępny moduł głosu opisany w etap-2/GLOS.md, bez odbioru Windows.
Etap 2.5a ma implementację do odbioru na Windows; etapy 2.5b–6 są planem. Każdy moduł kończy się testem zachowania,
awarii i odzyskiwania. Brak terminów, gwarancji wydajności i ukrytych usług.

| Etap | Zakres i zależności | Gotowe, gdy… |
|---|---|---|
| 1 | Windows, SQLite WAL, Python lokalny, llama-server CUDA, Web HTTP localhost, Gaming, backup/reset/uninstall | START na czystym Windows przygotowuje aplikację, login i historia przetrwają restart; SSE dociera przed końcem odpowiedzi; idempotencja i FK działają; Gaming kończy proces, WYLACZ kończy oba; backup odtwarza rozmowy; reset unieważnia sesje; uninstall domyślnie zachowuje dane; długa rozmowa nie przekracza budżetu tokenów; brak nieautoryzowanego dostępu |
| 2 | STT/TTS natywnie, PTT Web, początkowo CPU; profil Whisper small + System.Speech próbny, finalny dobór po pomiarze Windows | PL/EN: nagranie, transkrypcja, odczyt, cancel; brak audio po anulowaniu; urządzenie mikrofonowe niedostępne daje czytelny błąd; procesy zamykane WYLACZ; bez cloud |
| 2.5a | Upload, OCR, VLM, prywatne pliki NTFS, osobny ograniczony proces dekodera | Walidacja rzeczywistego typu/rozmiaru, timeout i limit RAM, brak dowolnych ścieżek, usuwanie oryginału i pochodnych; injection obrazu nie zmienia uprawnień; przełączenie GPU między tekstem/VLM bez OOM; samo Job Object nie jest sandboxem |
| 2.5b | RAG na sqlite-vec, SQLite źródła/chunki/ACL, lokalny embedding | DLL Windows i ładowanie rozszerzeń zweryfikowane; wyszukiwanie właściciela nie zwraca cudzych źródeł; restart/resume indeksowania; usuwanie pochodnych; spójny backup plików+bazy+wektorów; cytaty i jakość PL/EN zmierzone |
| 2.5c | Resumable upload i wizualne embeddingi | Wznawianie przerw bez duplikatów, oddzielne przestrzenie modeli/wymiarów; zmiana modelu tworzy nowy indeks; benchmark jakości i czasu na 8 GB VRAM |
| 3 | Cardputer, oddzielna bramka TLS/WSS, tokeny urządzeń, pairing/revoke | Tekst/reconnect/dedup, utrata urządzenia i revoke; nieużywanie sesji owner jako tokenu; audio i miniatury po pomiarze RAM/łącza; R4 po reauth; brak publicznego przekierowania lokalnego HTTP |
| 4 | Agent i typowane narzędzia, polityka, najpierw konektory tylko do odczytu | Złośliwy mail/strona/OCR nie uruchamia poleceń i nie zatwierdza akcji; test deny i izolacji właścicieli; osobne zgody na zapis; konta łączone tylko na wyraźne polecenie |
| 5 | Trwały worker Windows, harmonogram w SQLite, powiadomienia i koordynacja GPU | Lease/heartbeat, krótkie transakcje, restart bez podwójnego efektu, outcome_unknown przy niepewności; sen PC i wznowienie obsłużone; gaming wstrzymuje GPU zadań; autostart Task Scheduler tylko po osobnej decyzji |
| 6 | Android natywny, PTT/widget, prywatne powiadomienia, bezpieczna bramka | Historia i synchronizacja po offline, revoke, Keystore, test wersji Android i ograniczeń tła; wybór push lokalny/FCM jawny, brak ukrytego wysyłania treści rozmów |

## Kryteria odbioru etapu 1
Automatyczne: rzeczywisty SQLite, FK między rozmową i wiadomością, rollback,
idempotencja współbieżna, sesje/CSRF/Host/proxy, SSE replay i transmisja HTTP,
import bez duplikatów, backup/restore/reset, procesy start/stop/awaria/timeout,
SHA, traversal archiwum, kontekst tokenizer i paginacja.
Natywne: instalator PowerShell, ACL, prywatny Python, brak wymogu uprawnień
administratora poza ewentualnym instalatorem Microsoft VC, CUDA i Windows Job,
pomiary VRAM, test WYLACZ i odinstalowania. Brak środowiska = NIE URUCHOMIONO.

Przyszła kolejka SQLite ma jednego koordynatora zapisów, busy_timeout i retry;
nie przenosimy dosłownie SKIP LOCKED/advisory locks z PostgreSQL. Jeżeli pomiary
wykażą ograniczenia SQLite, zmiana silnika wymaga osobnej decyzji właściciela.

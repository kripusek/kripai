# Gaming — natywny Windows
Przycisk zapisuje normal/gaming i anuluje queued/preparing/generating.
Wątek backendu czyta żądanie; wyłącznie właściciel uchwytu Popen może kończyć
uruchomiony przez siebie llama-server.exe. Tryb gaming: terminate, czekanie,
w razie timeout kill, potwierdzenie końca procesu. Tryb normal: stała lista
argumentów, lokalny GGUF i klucz z pliku; gotowość przez chronione /v1/models
oraz /health. Timeout 180 s, błąd i ponawianie po 30 s. Panel pokazuje stan.
Nie wykonujemy poleceń przekazanych przez API lub model. Brak socketów Docker,
operatora WSL i plików do ręcznego przełączania. WYLACZ kończy też model.

Windows Job Object kill-on-close zabezpiecza proces potomny przy awarii
backendu; nie jest to sandbox narzędzi agenta. Stan stopped potwierdza koniec
procesu, nie zmierzone wolne GB. Pozostałe programy mogą nadal zajmować VRAM.
Przełączenie przerywa aktywną odpowiedź; ukończona historia pozostaje w SQLite.

Test właściciela: wyślij pytanie, kliknij Gaming, poczekaj na „model wyłączony”,
sprawdź brak procesu KripAI llama-server w Menedżerze zadań oraz spadek pamięci
GPU. Wróć do rozmów, poczekaj na gotowość i wyślij następne pytanie.

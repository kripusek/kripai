# Pomiar VRAM w panelu modelu

03.11.2026. „Tryb i stan systemu” otwiera panel „Model i karta graficzna”.
Oprócz przycisków Gaming pokazuje pomiar pamięci kart NVIDIA, czas odczytu,
kontekst 4096 i limit 2048 tokenów na porcję odpowiedzi. Pomiar można odświeżyć;
backend buforuje wynik przez 5 sekund. Nie uruchamiamy ciągłego monitoringu.

To zajętość całej karty, również innych aplikacji, a nie tylko llama-server.
Wartość „wolne” pochodzi ze sterownika. Used + free mogą być mniejsze od total
ze względu na rezerwy sterownika. Nie jest to gwarancja udanej alokacji modelu
ani pomiar budżetu WDDM/pamięci współdzielonej procesu. Po przełączeniu Gaming
odśwież pomiar i sprawdź czas próbki. Wyłączenie modelu nie zamyka innych programów.

Provider używa stałych ścieżek System32 lub NVIDIA NVSMI w Program Files,
nie PATH ani komendy z rozmowy. Wyłącznie --query-gpu i CSV, bez parametrów
zmieniających sterownik, zegary czy zasilanie. Proces ma timeout 3 s; do parsowania
przyjmujemy do 16 KiB i do 16 kart, z jawną flagą limitu. To zaufany program
sterownika, nie ogólny sandbox obcego narzędzia. stderr nie trafia do modelu/logów.
Brak CLI, timeout i nieprawidłowa odpowiedź zwracają available=false, nie zero
wolnej pamięci. Bez pomiaru aplikacja nadal działa.

GET /api/v1/system/gpu wymaga sesji i kontroli Host. Odczyt pozostaje GET
zgodnie z dotychczasowym kontraktem; nie zmieniono globalnego Origin/CSRF.
Nie przyjmuje komend ani parametrów urządzenia. Wynik nie jest narzędziem modelu
ani uprawnieniem do działań. Wylogowanie czyści panel i odrzuca spóźnione odpowiedzi.

Windows: 217 testów Python (216 OK, 1 symlink pominięty), Node 58/58.
Sprawdzono CSV/rezerwy/duplikaty/N/A/limity, prawdziwe procesy sukces/błąd/timeout,
cache/kopie danych, sesję/Host, bezpieczne renderowanie i spóźnioną odpowiedź.
Rzeczywisty sterownik RTX 3060 Ti przez autoryzowane API fixture zwrócił
7038/8192 MiB zajęte, 987 MiB wolne. Konto i kontroler w tej próbie były
kontrolowane; nvidia-smi i GPU rzeczywiste. Nie logowano się hasłem owner.
Chrome headless: desktop i 390 px, pomiar w nowym ciemnym panelu bez overflow.
API przeglądarki było kontrolowane i zasilone rzeczywistą próbką pomiaru.

Kod: app/gpu.py, endpoint w app/main.py, web/gpu.js, panel/CSS i testy.
Start nadal START.cmd. Bez migracji i nowych zależności. Pełny raport:
PANEL_GPU_TESTY.txt. Inference regresji kontrolowane, SQLite/procesy realne.
Mikrofon PL/EN, reinstall/uninstall i budżet WDDM nie są odbiorem tego modułu.

Kontrakt: [NVIDIA System Management Interface](https://docs.nvidia.com/deploy/nvidia-smi/index.html).

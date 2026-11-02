# Decyzje — nadrzędne od 30.10.2026
Właściciel jawnie polecił poniższe zmiany względem poprzedniej architektury.
1. Windows 11 x64 natywnie; bez WSL2, Dockera, PostgreSQL i Caddy.
2. SQLite WAL, foreign_keys=ON, krótkie BEGIN IMMEDIATE. Jeden backend i jeden
   worker generowania. Historia lokalna, transakcje i idempotencja zachowane.
3. Oficjalny llama-server.exe z CUDA i lokalnym GGUF, prywatny proces potomny.
   Brak instalacji globalnego CUDA Toolkit; DLL CUDA z tej samej publikacji.
4. Web i API z jednego backendu na http://localhost:8765, nasłuch 127.0.0.1.
   HTTP jest świadomym wyborem wyłącznie lokalnym, bez tunelu/LAN.
5. Jedno START.cmd przygotowuje program; WYLACZ.cmd kończy backend i model.
6. Kliknięcie Gaming zatrzymuje proces modelu; powrót uruchamia go i sprawdza
   gotowość. Nie deklarujemy liczby zwolnionych bajtów VRAM bez pomiaru.
7. Backup Online Backup API, odzyskiwanie, reset hasła i odinstalowanie.
   Dane/kopie poza folderem programu. Odinstalowanie nie usuwa ich domyślnie.
8. Długa historia pozostaje w SQLite; stronicowanie UI i tokenizowany kontekst
   ostatnich pełnych tur. Brak obietnicy pamiętania całej rozmowy przez model.
9. RAG w planie: sqlite-vec zamiast pgvector. Rozszerzenie DLL z przypiętym
   SHA i przeglądem zgodności Windows; brak ładowania rozszerzeń z treści/modelu.
10. Rozpoczęto etap 2 zgodnie z kolejnym poleceniem właściciela. Etap 2.5a rozpoczęto na kolejne polecenie właściciela; etapy 2.5b–6
    pozostają planem. Zachowane: lokalność, zgody na
    efekty zewnętrzne, izolacja właścicieli, brak autozatwierdzeń z danych.

Istniejąca baza PostgreSQL nie jest automatycznie konwertowana z plików woluminu.
IMPORT_HISTORII.cmd odczytuje rozmowy zalogowanego owner przez stare lokalne
API HTTPS, zachowuje ID/treść/czas i zapisuje transakcyjnie. Nie przenosi
starych sesji, sekretów, kolejek ani zdarzeń; nie usuwa starej bazy.

11. Etap 2 — profil próbny do pomiaru: Whisper.cpp b5454 CPU, model small
    wielojęzyczny (MIT, około 488 MB), odczyt przez lokalny System.Speech
    z Windows PowerShell 5.1. Głosy systemowe podlegają licencji Windows; to
    nie otwarty model TTS i nie usługa chmurowa. Dobór nie jest finalnym
    potwierdzeniem jakości PL/EN ani wydajności na komputerze właściciela.
12. Nagrywanie start/stop przyciskiem, maks. 30 s; tekst najpierw do korekty,
    brak automatycznego wysłania. Odczyt wyłącznie na kliknięcie. Bez stałego
    nasłuchiwania, klonowania głosu, zapisu nagrań w historii i fallbacku cloud.
    Gaming wyłącza również zadania głosu.

13. Po zgłoszeniu błędów rozpoznawania przez właściciela profil STT zmieniono
    z base na small wielojęzyczny. To próba poprawy jakości, nie potwierdzony
    wynik na zgłoszonym nagraniu. Bez automatycznych zamian rozpoznanych słów.

14. Etap 2.5a: PNG/JPEG/PDF, oryginał i podgląd jako BLOB w SQLite na prywatnym
    NTFS. Dzięki temu Online Backup obejmuje pliki i bazę w jednym obrazie.
    Dane rozpakowane wyłącznie w prywatnym katalogu tymczasowym, sprzątanym
    po zadaniu i przy starcie. 8 MiB/plik, 50 plików i 200 MiB łącznie.
15. Pillow 13.0.0 + pypdfium2 5.14.0 w osobnym procesie z limitem 512 MiB
    i 20 s. Dekodowanie zaczyna się dopiero po przypisaniu Windows Job Object.
    To ograniczenie zasobów i cyklu życia, nie pełna piaskownica bezpieczeństwa.
16. Qwen3-VL-4B-Instruct Q4_K_M, kwantyzacja Unsloth, projektor F16 na CPU,
    obraz do 1024 px i 1024 tokenów; llama.cpp b12000. SHA/revizja przypięte
    w vision-lock.json. Profil próbny — Windows/CUDA/VRAM wymagają pomiaru.
    Właściciel procesu kończy model tekstowy przed startem VLM i odwrotnie.
    Żądania tekstowe nie wchodzą podczas analizy obrazu; Gaming przerywa oba.
17. Jedna wybrana strona PDF. Najpierw warstwa tekstowa, przy jej braku OCR
    generatywny. Wynik do korekty; bez automatycznego wysyłania do rozmowy.
    Kopia przed usuwaniem; usunięty plik może pozostać w starszych kopiach
    do ich rotacji. Nie obiecujemy bezpiecznego wymazania sektorów dysku.

18. Na prośbę właściciela: zdjęcie dołączane bezpośrednio do wiadomości przez
    Ctrl+V, przeciągnięcie lub wybór pliku. Jeden PNG/JPEG do 8 MiB, miniatura
    lokalna, upload dopiero na Wyślij. Pytanie i obraz zapisane atomowo jako
    wiadomość/run; VLM odpowiada przez SSE w historii. Panel PDF pozostaje.
19. Migracja 3 wiąże wiadomość, plik i sesję; kopia przed zmianą schematu.
    Usunięcie pliku zeruje odwołanie, bez cichego fallbacku do analizy tekstowej.
20. Lokalny Marked 17.0.5 MIT wyłącznie tokenizuje Markdown. Renderer buduje
    dozwolony DOM, bez innerHTML i wykonywania HTML/kodu odpowiedzi.
    Podstawowy TeX jako MathML; nieznane polecenia pozostają źródłem.

21. Poprawka cutoff: OUTPUT=2048 zamiast 768; CONTEXT=4096 bez zmiany. Tokenizer rezerwuje nowy budżet, trimując starsze tury. finish_reason=length oznacza zachowany, niepełny wynik i error_code=output_limit w ukończonym run. Przycisk Kontynuuj przygotowuje osobną wiadomość z końcówką do edycji.

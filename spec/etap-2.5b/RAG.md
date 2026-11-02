# Etap 2.5b — pamięć tekstowych PDF, pierwszy działający zakres

## Obsługa
Windows: git pull --ff-only → START.cmd → Ctrl+F5. START instaluje dodatkowy
wheel sqlite-vec i próbuje pobrać model E5 (131624960 B, około 126 MiB).
Brak modelu nie blokuje zwykłego tekstowego czatu, lecz RAG zgłasza rag_not_installed.
Biblioteka sqlite-vec jest wymagana przez nowy schemat bazy, instalowana przed testami.

W panelu „Zdjęcia i PDF” dodaj PDF, potem otwórz „Pamięć dokumentów”. Kliknij
Indeksuj; postęp zapisuje się po każdej stronie. Gotowe dokumenty można zaznaczyć
(do 5) i zadać pytanie w zwykłym czacie. Źródła pod odpowiedzią mają nazwę,
stronę, wycinek i pobranie oryginału. Zaznaczenie pozostaje do wyczyszczenia;
nie jest to automatyczne przeszukiwanie wszystkich prywatnych plików.

## Model i zasoby
Multilingual E5-small Q8_0 z cstr, rewizja i SHA w scripts/rag-lock.json, 384 wymiary.
Encoder uruchamiany na czas zadania jako osobny llama-server, port 127.0.0.1:8767,
prywatny klucz z pliku, CPU (--device none, --n-gpu-layers 0, --no-op-offload),
4 wątki, kontekst/batch/ubatch 512, mean pooling. Job Object 1536 MiB na Windows.
Nie powstaje drugi model offloadowany na GPU. Narzut sterownika CUDA i faktyczne
RAM/VRAM na docelowym Windows wymagają pomiaru. Ten sam przypięty llama.cpp b12000.

Próba prawdziwego GGUF wykazała brak tokenizer.ggml.token_type_count wymagany
przez loader b12000. Jawne --override-kv tokenizer.ggml.token_type_count=int:2
odpowiada type_vocab_size=2 oryginalnego config.json E5; poprawka jest w locku,
a przestrzeń indeksu zawiera type2. Nie zmieniamy bajtów pobranego modelu.
Test rzeczywistego encodera na Linux oraz mini-próba PL/EN są zapisane w raporcie.

Prefiksy query:/passage:, normalizacja L2, kontrola 384 skończonych składowych
bez wektorów zerowych. Fragmenty do 700 znaków, overlap 80, dopasowywane
prawdziwym tokenizerem do <=480 tokenów. Pytanie <=500 tokenów po prefiksie.
Brak cichego truncation. Brak zamiennego modelu ani niejawnego fallbacku API.

## Dane i cykl życia
Migracja 4, kopia przed DDL; migracje 1–3 bez zmian. rag_documents zawiera
owner/session/space/status/next_page/chunks. rag_chunks i rag_vectors zapisują
się atomowo z checkpointem strony. Limit globalny 20000 fragmentów.
Błąd strony nie zatwierdza jej fragmentów. Wznów zachowuje wcześniejsze strony;
Przebuduj robi kopię, usuwa stary indeks i zaczyna od nowa. Powtórne zlecenie
gotowego indeksu nie dubluje fragmentów. Zmiana przestrzeni wymaga przebudowy.

Restart po awarii zmienia indexing na queued; ważna sesja pozwala wznowić od
checkpointu. Gaming, wylogowanie, anulowanie i poprawne wyłączenie wstrzymują
zadanie; wznowienie z panelu wiąże je z obecną sesją. Jeden encoder naraz;
RAG pytania podczas indeksowania zwraca rag_busy, zwykły chat pozostaje dostępny.
Dekoder PDF dzieli istniejący limit i blokadę media, RAM 512 MiB, timeout 20 s.

Usuń indeks robi kopię i usuwa wektory, chunki i zapisane wycinki cytowań (także z replay SSE), PDF
pozostaje. Usuń plik usuwa też cały indeks i wycinki. Odpowiedzi modelu w historii
pozostają; starsze kopie mogą zawierać usunięte dane. Backup Online Backup API
obejmuje źródła+BLOB+chunki+vec0+checkpoint; waliduje spójność obu stron indeksu.

## Wyszukiwanie, ACL i kontekst
SQLite-vec 0.1.6 z przypiętym SHA DLL/SO. Rozszerzenie ładowane wyłącznie ze
stałej ścieżki, po kontroli SHA i wersji; enable_load_extension wyłączane w finally.
W vec0: owner_id i document_id jako tekstowe partition key. Właściciel i gotowy
stan sprawdzane przed wyszukiwaniem i po obliczeniu pytania. KNN na każdym
wybranym dokumencie zawiera oba filtry; dopiero wyniki tych ograniczonych zapytań
są łączone i sortowane (do 3 fragmentów). Nie filtrujemy globalnego top-k.
Test z lepszymi obcymi i niewybranymi wektorami sprawdza tę różnicę.

document_ids jest zapisane w run razem z wiadomością i kluczem idempotencji.
Źródła jako niezaufane dane JSON w systemowym kontekście; nie mogą uruchomić
narzędzi ani zatwierdzić działań. Nie stosujemy SQL ani ścieżek podanych przez LLM.
Prawdziwy tokenizer tekstowego modelu rezerwuje istniejący budżet 4096/2048;
niemieszczące się fragmenty są odrzucane i nie pojawiają się w źródłach odpowiedzi.
SSE rag.sources i tabela message_sources przechowują użyte wycinki; historia
filtruje je według obecnej własności pliku. Cytowanie nie gwarantuje prawdziwości
wygenerowanej odpowiedzi ani poprawnego wykorzystania każdego fragmentu.

## Granice i odbiór
Na razie tylko PDF z warstwą tekstową, do 50 stron/8 MiB. Pusta/skanowana strona
zatrzymuje indeks z rag_no_text; strona >12000 znaków z rag_page_too_long.
Nie oznaczamy takiego indeksu jako gotowego. Brak OCR całego skanu i indeksowania
PNG/JPEG/TXT/DOCX. Brak semantycznego streszczania, rerankera i kalibrowanego
progu trafności. Mini-test 3 zapytań nie zastępuje benchmarku PL/EN/długich PDF.

Windows do odbioru: START z czystego repo, DLL+CPython, dwustronicowy PDF → indeks
→ pytanie i źródła → restart → pauza/wznów → Gaming → usuń → backup/restore.
Potwierdzić brak drugiego modelu GPU i zmierzyć RAM/VRAM. Wyniki Linux nie
zaliczają tych testów. RAG nie oznacza odebrania całego etapu 2.5b na Windows.

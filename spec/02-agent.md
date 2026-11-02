# 02 — Rozmowa, kontekst i przyszły agent
Etap 1 nie ma narzędzi, RAG, internetu ani wykonywania poleceń z odpowiedzi.
Historia jest trwała i kompletna; model widzi system + ostatnie pełne tury.
Do wyboru kontekstu używamy /apply-template i /tokenize tego samego llama-server.
Budżet: 4096 tokenów minus 2048 na odpowiedź i 128 rezerwy. Brak tokenizera lub
zbyt długa pojedyncza wiadomość kończy run jawnym błędem, nie udawanym sukcesem.
Czytamy maksymalnie 200 ostatnich wiadomości do budowy kontekstu; starsze
pozostają w SQLite. SSE context.info podaje liczbę pominiętych wiadomości.
UI pobiera po 50 wiadomości z kursorem seq, zaczynając od najnowszych.

RAG etapu 2.5b: pierwszy zakres opisuje etap-2.5b/RAG.md; tabele rag_documents/rag_chunks oraz rag_vectors vec0 w sqlite-vec.
Każdy rekord ma owner_id, source_id, wersję embeddingu, wymiar i status indeksu.
Treść, embedding i metadane muszą mieć spójny cykl utworzenia/usunięcia.
Wyszukiwanie zawsze ogranicza zbiór do owner_id i dozwolonych dokumentów;
nie wolno wyszukać globalnie top-k, a potem uznać samego odfiltrowania za ACL.
Wybrana wersja sqlite-vec wymaga testu filtrów/partycji i planu zapytania.
DLL ładowana wyłącznie przez backend z lokalnej listy i SHA; następnie
wyłączamy możliwość dalszego load_extension. Nigdy arbitralne SQL od modelu.

Zmiana modelu lub wymiaru oznacza nową przestrzeń wektorów i pełną przebudowę.
Indeks można odtworzyć ze źródeł, backup musi obejmować źródła i metadane.
Embeddingi tekstowe i wizualne mają oddzielne przestrzenie. Cytaty wskazują
źródło/chunk, model ma ujawniać brak danych. OCR i znaleziony tekst są danymi
niezaufanymi, nie instrukcjami nadania uprawnień.

Etap 4: oddzielne typowane narzędzia, polityka deny-by-default i zgody na
konkretne skutki. Sam tekst modelu, pliku lub strony nie jest zgodą właściciela.
Nie wykonujemy poleceń shell pochodzących z LLM.

Etap 2.5a: odczyt wybranego obrazu/strony PDF bez narzędzi. Wynik do ręcznej korekty i wysłania; nie pamięć dokumentów ani RAG.

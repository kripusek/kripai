# Pamięć obrazów — etap 2.5c

Panel **Pamięć obrazów** jest dostępny w historii oraz pod przyciskiem „+”.
Dodaj własny PNG, JPEG albo PDF w panelu plików. Przygotuj opcjonalny koder CPU,
zindeksuj pliki, zaznacz do pięciu gotowych i wpisz krótki opis. Wyniki otwierają
oryginalny załącznik i właściwą stronę PDF przez istniejący dekoder. Nie wysyłają
wiadomości ani nie uruchamiają VLM. Samo podobieństwo nie potwierdza zawartości.

Koder SigLIP2 base patch16/224 INT8 pochodzi z przypiętego eksportu ONNX
`onnx-community/siglip2-base-patch16-224-ONNX`, revision
`ba1f3b0843f24bc5417d38e19c37b287d719b2f4`. ONNX Runtime 1.31.1,
tokenizers 0.23.3 i numpy 2.5.4 pracują wyłącznie w osobnym procesie prywatnego
Pythona 3.13. Jawny provider CPU, dwa wątki, limit procesu 3 GiB RAM;
rozruch do 60 s, pojedyncze kodowanie do 30 s. Proces zamyka się po zadaniu.
Nie zmienia konfiguracji llama-server CUDA ani kontekstu rozmowy.

Przygotowanie wymaga właściciela, aktywnej sesji i CSRF. Publiczne pobrania
modeli/wheels nie używają kont ani tokenów. SHA256/rozmiary/wersje są w
`scripts/visual-lock.json`; runtime jest oddzielny od głównego Pythona.
Pierwsza rzeczywista instalacja pobrała 6 assets i 21 wheels: 526 458 449 B
po rozpakowaniu, 1976 plików, 25,516 s na tej maszynie. Limit pobrania i
rozpakowania to 1 GiB, przygotowanie do 600 s; wymagane 2 GiB wolnego miejsca.
Nieznany katalog pozostaje nienaruszony. Naprawa zachowuje rozpoznany poprzedni
runtime i ma rollback. Integralność sprawdzana przed wykonaniem kodera;
odpytywanie postępu nie hashuje ponownie całej instalacji.

Migracja 008 dodaje osobne metadane/strony i `visual_vectors` (sqlite-vec,
768 wymiarów, cosine). E5/384 pozostaje osobną przestrzenią. Tożsamość obejmuje
revision, INT8 i wersję przetwarzania v1. Zmiana przestrzeni wymaga jawnej
przebudowy po kopii; inny wymiar wymaga nowej przestrzeni/tabeli i migracji.
Indeks nie miesza wektorów różnych modeli.

Każdy KNN ma wewnętrzne ograniczenia owner, wybranego dokumentu i przestrzeni.
Nie filtrujemy dopiero globalnego top-k. Wynik obejmuje do trzech stron z
wybranych plików. Limit indeksu: 2500 stron, oryginalne limity plików bez zmian.
Indeksowanie każdej strony używa rzeczywistego dekodera i atomowo zapisuje
wektor, metadane oraz checkpoint. Generacja zadania, sesja, Gaming, właściciel
i numer strony są sprawdzane ponownie w transakcji zapisu. Stary proces nie
odtworzy usuniętego/przebudowanego indeksu. Wstrzymanie i ponowienie zachowują
ukończone strony; restart wznawia przerwane zadanie z ważną sesją.

E5 i pamięć obrazów mają wspólną blokadę CPU. Dekoder ma wspólny limit z panelem
plików. Gaming lub wylogowanie wstrzymują pracę. Usuwanie/przebudowa indeksu
wymagają udanej kopii; usunięcie pliku czyści także wektory. SQLite Online Backup
obejmuje wektory, strony i źródła; walidacja odrzuca niespójny indeks.

Opis: do 500 znaków i 64 tokenów kodera, bez cichego ucinania. Wyniki nie są
OCR, podpisem obrazu ani dowodem, że model rozmowy obejrzał zdjęcie. Pierwszy
pomiar jakości dotyczy wyłącznie sześciu syntetycznych ilustracji: 12/12 opisów
PL/EN dało poprawny top-1. Nie jest to ocena ogólnej jakości zdjęć lub wykresów.
Pełny raport potwierdzonych prób: `TESTY_PAMIEC_OBRAZOW.md`.

API: `/api/v1/visual/status`, `/prepare`, `/documents`,
`/documents/{aid}/index`, `/pause`, DELETE `/documents/{aid}` i `/search`.
Wyszukiwanie przyjmuje `{query, attachment_ids}`. Dane plików/opisów pozostają
lokalne; przygotowanie pobiera tylko publiczne przypięte zależności.

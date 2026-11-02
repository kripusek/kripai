# Etap 2.5a — prywatne obrazy i PDF

PNG/JPEG/PDF do 8 MiB; maks. 16 mln pikseli obrazu, 50 stron PDF,
50 plików i 200 MiB oryginałów wraz z podglądami. Jeden dekoder naraz.
Wybrana strona renderowana do PNG do 1024 px. Metadane podglądu usunięte,
orientacja EXIF zastosowana, przezroczystość na białym tle. Oryginał zachowany.
PDF nie uruchamia JavaScript ani akcji; formularze nie są renderowane.
Warstwa tekstowa: do 12000 znaków; nie jest to OCR skanu. Dłuższy dokument
czytany pojedynczymi stronami, bez automatycznego indeksowania.

Dekoder: osobny proces, Job Object 512 MiB na Windows, timeout 20 s,
na Linux QA RLIMIT_AS i CPU. Brak pełnego sandboxa. Pliki klienta nie mogą
wyznaczać ścieżek. Upload po sesji/Origin/CSRF, również przy chunked body.
Właściciel sprawdzany przy podglądzie, pobieraniu, stronie, analizie i usuwaniu.
Oryginał serwowany jako attachment/octet-stream z rozszerzeniem rzeczywistego
formatu, nigdy HTML. Wyniki w DOM tylko jako tekst, bez innerHTML.

Dane w attachments (SQLite BLOB); migracja 2 z kopią przed zmianą starej bazy.
Restore akceptuje wersję 1 i 2, uaktualnia starszą, unieważnia sesje.
Usunięcie wymaga kopii i usuwa oryginał/preview/tekst/analizę z aktywnej tabeli.
Starsze kopie nadal mogą je zawierać. Zachowywanych jest 14 kopii.

VLM: Qwen3-VL-4B-Instruct Q4_K_M + mmproj F16, około 3.34 GB do pobrania.
Zaufany kod wybiera profil text/vision, nigdy treść pliku. Jedna instancja
llama-server, projektor CPU (--no-mmproj-offload), GPU tylko dla modelu.
Przełączenie czeka na zakończenie starego procesu. Po błędzie/anulowaniu
wraca profil tekstowy. Gaming zatrzymuje także dekoder i analizę.
Żądanie VLM ma wyłącznie obraz PNG data URI i tekst, bez tools i zewnętrznych URL.
Nie ma agentowych efektów ani automatycznego zatwierdzania instrukcji z obrazu.

Odbiór Windows: README. Testy w docs/WYNIKI_TESTOW.txt. Wynik testów Linux
nie potwierdza CUDA, natywnego Job Object ani liczby zwolnionych bajtów VRAM.
RAG sqlite-vec pozostaje etapem 2.5b; brak pamięci całych dokumentów.

Zdjęcia można również wklejać bezpośrednio do rozmowy — szczegóły CZAT.md. Migracja 3; kopie wersji 1/2/3 obsługiwane.

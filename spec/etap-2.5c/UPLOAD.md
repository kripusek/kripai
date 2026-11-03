# Etap 2.5c — pierwszy zakres: wznawialne dodawanie plików

Rozpoczęty na polecenie właściciela dodawania kolejnych funkcji. To pierwszy
zakres 2.5c; wizualne embeddingi i ich oddzielna przestrzeń pozostają planem.
Architektura Windows/SQLite/localhost i profil modeli pozostają bez zmian.

PNG/JPEG/PDF nadal do 8 MiB, dekoder do 50 stron PDF. Kompozytor i panel plików
wysyłają fragmenty do 512 KiB. Po przerwaniu, odświeżeniu strony i ponownym
wybraniu tego samego pliku transport pyta o potwierdzony postęp i wysyła resztę.
Przeglądarka musi nadal mieć tę samą sesję logowania i zapisane metadane wznowienia.
Wysyłka wygasa po godzinie bez przyjęcia nowej porcji. Nowe logowanie/inna sesja
nie dostają dostępu do starych bajtów; po wygaśnięciu zaczyna się od nowa.

## Przechowywanie i spójność

Migracja 007 dodaje `upload_sessions`. Fragmenty są w prywatnym SQLite, objęte
zwykłą kopią bazy. W przeglądarce zapisujemy najwyżej 12 rekordów metadanych
ID/nazwa/rozmiar/SHA256 w sessionStorage, bez bajtów i kluczy. Logout czyści ten
stan i unieważnia spóźnione operacje. Brak sessionStorage ogranicza wznowienie
po przeładowaniu; nie oznaczamy takiego wznowienia jako gwarantowanego.

POST init z tym samym UUID i metadanymi zwraca stan. PUT sprawdza offset;
identyczne ponowienie wcześniejszych bajtów jest akceptowane, inne bajty lub luka
dają konflikt. Nowe porcje są atomowo dopisywane. Przed dekodowaniem cały SHA256
musi się zgadzać. INSERT załącznika, wyczyszczenie bufora i potwierdzenie są jedną
transakcją. Powtórzenie finalizacji zwraca ten sam plik, bez drugiego dekodowania.
Usunięty finalny załącznik nie jest odtwarzany automatycznie.

Wewnętrzna generacja rekordu blokuje zatwierdzenie starego dekodowania po
usunięciu i ponownym utworzeniu tego samego ID. Tuż przed zapisem ponownie
sprawdzamy sesję, Gaming i anulowanie w tej samej transakcji. Błąd dekodera,
anulowanie lub rollback zachowują potwierdzone bajty do ponowienia.

Najwyżej 3 nieukończone wysyłki jednocześnie. Bufory wliczają się do istniejącego
limitu danych 200 MiB; finalizacja nie liczy przenoszonych bajtów drugi raz.
Istniejący limit 50 finalnych plików nadal obowiązuje. Przed usunięciem wygasłych
lub jawnie odrzuconych bajtów powstaje kopia SQLite, a blokada zapisu obejmuje
kopię i usunięcie. Błąd kopii pozostawia dane. Kopie podlegają dotychczasowej rotacji.

## Interfejs

Wybierz plik jak dotychczas; zobaczysz procent i liczbę bajtów. „Wstrzymaj”
zatrzymuje aktywną operację, nie usuwa zapisanej porcji. Wybierz ten sam plik,
żeby wznowić. „Usuń niedokończone wysyłki” wymaga jawnego potwierdzenia i nie
usuwa gotowych załączników. Wygaśnięcie lub usunięty plik daje czytelny błąd;
kolejny wybór tworzy nowe ID. Ostateczna walidacja pliku pozostaje obowiązkowa.

Przesyłanie nie wysyła wiadomości ani nie uruchamia modelu. Kompozytor zachowuje
dotychczasowe wysyłanie zdjęcia dopiero na „Wyślij”; sam upload używa dekodera CPU.
Gdy nowy moduł transportu nie jest dostępny, działa dotychczasowa pojedyncza trasa.
Nie jest to implementacja standardu tus ani zwiększenie limitu rozmiaru plików.

HTTP: POST/GET `/media/uploads`, GET `/{id}`, PUT `/{id}/chunks?offset=N`,
POST `/media/jobs/{job}/uploads/{id}/complete`, POST `/media/uploads/discard`.
Sesja, Host, Origin i CSRF obowiązują; duży PUT jest autoryzowany przed buforowaniem.
Narzędzia modelu nie otrzymują żadnego z tych uprawnień ani dowolnych ścieżek.

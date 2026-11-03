# Wyszukiwanie wiadomości w historii

W panelu historii wpisz **Fragment wiadomości** i kliknij **Szukaj**. Przeszukujemy
treść własnych wiadomości użytkownika i asystenta, bez modelu i usług zewnętrznych.
To dopasowanie dosłownego fragmentu z Unicode casefold, bez rozróżniania wielkości
liter, nie wyszukiwanie semantyczne ani wyszukiwanie po tytułach. Query ma 2–120
znaków. Samo pisanie nie wysyła żądań. „Wyczyść” i logout usuwają query oraz wyniki.

Wynik pokazuje tytuł rozmowy, rolę, datę i do 240 znaków oryginalnego wycinka.
Kliknięcie otwiera dokładną wiadomość, również poza ostatnimi 50, i wyróżnia ją.
**Najnowsze** wraca do końca rozmowy; **↑ Starsze** pozwala czytać wcześniejszy
kontekst. Szkic pozostaje bez zmian. Nie przełączamy rozmowy podczas generowania
odpowiedzi. Mobilny sidebar pozostaje otwarty przy wyszukiwaniu i stronicowaniu;
wybór wyniku zamyka go po otwarciu rozmowy.

Porcja sprawdza najwyżej 2000 własnych wiadomości i pokazuje do 20 dopasowań.
**Przeszukaj starsze** kontynuuje od ostatnio sprawdzonego seq. Brak trafień w
porcji nie oznacza braku w całej historii — kursor pozostaje dostępny, jeśli są
starsze wiadomości. Kolejne porcje zastępują listę, żeby nie gromadzić jej bez
limitu w DOM. UI pokazuje licznik sprawdzonych wiadomości i niepełny zakres.

SQLite czyta snapshot bez rezerwacji zapisu i filtruje właściciela przed LIMIT.
Tekst źródła nie jest zmieniany; fragment uwzględnia rozszerzenia casefold,
np. ß→ss, bez błędnego przesunięcia oryginalnego wycinka. Nowe wiadomości po
rozpoczęciu stronicowania pojawią się przy nowym wyszukiwaniu. To skanowanie
stronicowane, bez dodatkowego indeksu, biblioteki, migracji ani modelu.

GET `/api/v1/conversations/search?q=...&cursor=...` wymaga sesji. Wynik zawiera
`items`, `next_cursor`, `scanned_messages` i `partial`. GET wiadomości obsługuje
`at=seq`, niełączone z `cursor`: sprawdza własność rozmowy i istnienie dokładnego
punktu, zwracając stronę kończącą się tym seq. Obcego punktu nie można otworzyć.
Wylogowanie i zmiana query unieważniają późne odpowiedzi i stare przyciski.

Chrome/Playwright z izolowanym rzeczywistym API sprawdził 130 wiadomości:
wyszukanie starszego seq61, wyróżnienie, powrót do najnowszych, dwie porcje
wyników, zachowany szkic, mobilne 390 px oraz spóźniony wynik po logout. Brak
wysyłania wiadomości i żądań modelu. Raport: WYSZUKIWANIE_HISTORII_TESTY.txt.

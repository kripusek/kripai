# Bieżący moduł: zdjęcia w rozmowie i formatowanie

Właściciel doprecyzował zakres: bezpośrednie wklejanie obrazu jak w czacie,
bez ręcznego przenoszenia wyniku OCR. Miniatura lokalna, wysłanie dopiero przyciskiem.
Kryterium gotowości: zdjęcie + pytanie → jeden run → SSE → odpowiedź i obraz
w historii; bez duplikatów po ponowieniu. Cancel/Gaming/logout przerywają zadanie.

Migracja 3 message_images: message_id PK/FK, attachment_id FK SET NULL,
session_id FK SET NULL. Kontrola właściciela przed utworzeniem wiadomości.
Kopia przed DDL, migracje 1 i 2 bez zmian. Stare kopie są uaktualniane przy restore.
Usunięty plik w oczekującym run kończy się file_not_found, nie analizą bez obrazu.
Istniejący koordynator zatrzymuje tekst przed VLM i przywraca model po analizie.
Brak narzędzi/wykonywania poleceń z treści pliku. Nowe pytanie bez zdjęcia
korzysta tylko z tekstu historii, nie automatycznie z dawnych obrazów.

Formatowanie: lokalny Marked 17.0.5, wyłącznie lexer/tokens → dozwolone DOM.
Brak innerHTML/eval. Zdalne obrazy nieosadzane, linki tylko HTTP/HTTPS/mailto.
Kod jako tekst, kopiowany do schowka po kliknięciu. Aktualizacja streamu co 80 ms.
Podstawowe wzory TeX → MathML, limit długości/zagnieżdżenia; bez makr/URL/skryptów.
Nieznane komendy jako źródło. Testy UI na modelu DOM, nie test wizualny przeglądarki.

Instrukcja i ograniczenia: README. Raport dosłowny: docs/WYNIKI_TESTOW.txt.

02.11.2026 — lokalny lexer web/syntax.js: oznaczone bloki JS/TS, Python, HTML,
CSS, JSON, SQL, shell, PowerShell. Wyłącznie węzły span/textContent; bez eval,
innerHTML i CDN. To podstawowe kolorowanie leksykalne, nie pełny parser języka
ani sprawdzanie poprawności programu. Nieznany język, błąd, ponad 40000 znaków
lub 8000 tokenów: zwykły tekst. Kopiowanie zachowuje źródło.

# 04 — Urządzenia i kontrakty przyszłych etapów
Etap 1: wyłącznie przeglądarka na tym samym Windows. Schematy w schemas/
i przykłady w examples/ są zachowanym projektem protokołu, a nie wdrożeniem.

Etap 3 Cardputer: oddzielna bramka HTTPS/WSS z weryfikacją certyfikatu,
parowanie po lokalnym potwierdzeniu właściciela, unikalny sekret urządzenia,
revoke, ograniczenia uprawnień i wersjonowane wiadomości. Żadne hasło owner
ani sesja przeglądarki nie są tokenem urządzenia. Urządzenie toleruje nieznane
pola serwer→urządzenie; serwer ściśle waliduje dane urządzenie→serwer.
R4/operacje szczególnie wrażliwe wymagają ponownego uwierzytelnienia i zgody.
Transport zapewnia seq/ack/reconnect, rozmiar wiadomości, limity czasu i dedup.
Pamięć/miniatury/audio mierzymy na docelowym urządzeniu; nie zakładamy kamery.
OTA tylko podpisany manifest, monotoniczny licznik wersji i kontrola rollback;
nie implementujemy OTA w etapie 1. Dane z OCR i obrazów nie zatwierdzają OTA.

Etap 6 Android: ta sama bramka i revoke, sekrety w Android Keystore, ochrona
powiadomień przed ujawnieniem rozmów na ekranie blokady. FCM (jeśli wybrane)
nie oznacza lokalnego przetwarzania metadanych: wymaga osobnej decyzji.
Nie obiecujemy publicznego dostępu HTTP ani PWA na telefonie z localhost PC.
Zdalny dostęp powstanie dopiero po teście TLS, ACL, parowania i utraty urządzenia.

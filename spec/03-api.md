# 03 — Lokalny Web/API
http://localhost:8765, uvicorn bind 127.0.0.1, proxy_headers=False, jedna instancja.
FastAPI udostępnia statyczny interfejs; bez Caddy, certyfikatów i CORS.
Sesja losowa, w bazie SHA-256; cookie HttpOnly, SameSite=Strict, 12 h.
Secure=False wynika z lokalnego HTTP. Tego ustawienia nie wolno kopiować do
wdrożenia zdalnego. CSRF osobny token, dokładny Origin dla wszystkich mutacji,
Host tylko localhost:8765 i 127.0.0.1:8765; nagłówki tunelu/proxy odrzucane.
Login ma limit prób. Hasło scrypt z losową solą. Brak domyślnego hasła.
CSP self, brak inline script, no-store, tekst modelu renderowany textContent.
Limit body 16 KiB także bez Content-Length; Pydantic odrzuca dodatkowe pola.

Endpointy: auth/login/logout, me, conversations, messages, runs/cancel/events,
system/status i system/mode. Szczegóły w etap-1/openapi.yaml.
Własność rozmowy i runu sprawdzana każdorazowo. Idempotency-Key + hash treści
+ odpowiedź zapisane w jednej transakcji, 24 h. Powtórzenie nie tworzy zadania.
SQLite BEGIN IMMEDIATE zastępuje blokady advisory PostgreSQL.
SSE ma trwały seq na run, reconnect Last-Event-ID, ponowną kontrolę sesji,
bez buforującego proxy. Wiadomość assistant dopiero po pełnym zakończeniu;
częściowe fragmenty są zdarzeniami. Restart oznacza niedokończone runy failed.

llama-server: tylko 127.0.0.1:8766, losowy klucz z pliku; nie ma bezpośredniego
połączenia z przeglądarki. Tokeny nigdy nie trafiają do URL ani argumentów procesu.
/health upstream jest publiczny; gotowość wymaga też chronionego /v1/models.

Etapy zdalne 3/6 wymagają nowej bramki TLS, osobnych tokenów urządzeń, parowania,
revoke i rate limits. Obecnego portu HTTP nie wystawiamy przez Cloudflare Tunnel.

Głos (etap 2): POST voice/jobs/{UUID}/transcribe (audio/wav), speak (JSON)
i cancel. Dla transcribe po login/CSRF limit 960044 B; inne body nadal 16 KiB.
WAV jest PCM16 mono 16 kHz z dokładnym nagłówkiem, 0,25–30 s, bez metadanych.
Język pl/en, tekst TTS max. 1200 znaków na porcję. Wynik TTS: audio/wav.
UUID jest prywatny dla sesji, cancel zapisuje znacznik także przed startem.
Brak trwałego replay głosu: ponowienie UUID w ciągu 10 min odrzucane; maks.
256 UUID/10 min i jeden proces na aplikację. Głos nie tworzy wiadomości ani
runów. Sesja i Gaming sprawdzane co 0,1 s pracy procesu, timeout 90 s STT /
45 s TTS; rozłączenie klienta bez cancel ma ograniczenie czasu, nie replay.
CSP dopuszcza media blob: dla WAV, Permissions-Policy mikrofon tylko self,
kamera wyłączona. Dane tekstowe nie są poleceniem ani SSML.

Etap 2.5a: GET /files, GET/DELETE /files/{id}, GET /files/{id}/preview i /download. POST /media/jobs/{job_id}/files (raw body, query name), /media/jobs/{job_id}/files/{id}/page (page), /analyze (mode,question), /media/jobs/{job_id}/cancel. Wszystkie pod /api/v1, sesja/ACL; mutacje CSRF+Origin. UUID job jednorazowe w oknie 10 min. Upload do 8 MiB, pozostałe JSON 16 KiB. Status zawiera profile: text/vision.

MessageCreate: opcjonalne attachment_id UUID właściciela (PNG/JPEG). GET messages zwraca attachment_id/null. Odpowiedź obrazu używa istniejących run/events i cancel. Sesja, Origin, CSRF i limity uploadu zachowane.

Run zakończony przez limit wyjścia ma status completed i error_code=output_limit; treść częściowa pozostaje w historii. run.status SSE zawiera ten kod. Analiza pliku zwraca dodatkowo truncated (boolean). Zerwanie SSE bez DONE nadal zgłasza błąd.

RAG 2.5b: GET /rag/documents, POST /rag/documents/{aid}/index (rebuild=false),
POST /rag/documents/{aid}/pause, DELETE /rag/documents/{aid}, wszystko pod /api/v1.
Sesja, ACL, Origin i CSRF jak pozostałe operacje; brak dowolnych ścieżek/SQL.
MessageCreate.document_ids: do 5 gotowych PDF właściciela, bez jednoczesnego
attachment_id. Run zapisuje wybór; SSE rag.sources i messages.sources zawierają
użyte wycinki. Usunięcie indeksu usuwa je również z replay SSE. Szczegóły RAG.md.

Etap 4a: MessageCreate.allow_web/allow_github (false) zapisane w run z sesją.
Bez nowego endpointu wykonującego dowolne polecenia. SSE tool.activity i
 tool.sources; messages.tool_sources zawiera wycinki/URL. Obrazy i narzędzia
wysyłane osobno. Backup obejmuje tool_sources; migracja 5 z kopią.

4b rozszerza allow_web o web_search (Bing RSS) i odczyt otrzymanych wyników.
Do 2 rund/4 wywołań; lokalne notatki dla długiego tekstu. Brak nowego endpointu
ani migracji; format zapisanego oryginalnego wycinka źródła nadal max 1200 znaków.

# 05 — Stos i zasoby
Windows 11 x64; prywatny CPython 3.13.17 embeddable z python.org, przypięty SHA.
FastAPI 0.115.12, Pydantic 2.11.3, httpx 0.28.1, uvicorn 0.34.2.
Pełne wersje i SHA wszystkich wheels: scripts/vendor-lock.json. Pakiety są
częścią dystrybucji aplikacji; nie instalujemy pip ani globalnych bibliotek.
SQLite pochodzi z prywatnego CPython; test raportuje jego faktyczną wersję.

llama.cpp b12000 Windows x64 CUDA 12.4, serwer + cudart DLL z tej samej publikacji;
SHA i URL w scripts/llama-lock.json. Nie pobieramy dynamicznego „latest”.
Qwen/Qwen3-8B-GGUF Q4_K_M, przypięta rewizja i SHA w scripts/model-lock.json.
Model około 5 GB; pierwsze pobranie wznawiane i weryfikowane. Brak globalnego
CUDA Toolkit, ale aktualny sterownik NVIDIA jest wymagany. --list-devices
musi wykazać CUDA; nie maskujemy błędu cichym przejściem na CPU.
Kontekst 4096, jedna generacja naraz, limit odpowiedzi 2048. Jakość PL/EN,
rzeczywista szybkość, dopasowanie do 8 GB VRAM i odzyskanie pamięci wymagają
pomiaru na komputerze właściciela. Żadna liczba wydajności nie jest gwarantowana.

Przed dalszym wdrożeniem przegląd aktualizacji bezpieczeństwa zależności i
licencji. Nie włączamy autoaktualizacji binariów bez ich sprawdzenia.
sqlite-vec dopiero etap 2.5b: wersję i Windows DLL wybieramy i przypinamy wtedy;
projekt upstream jest przed 1.0, więc zgodność/API/backup wymagają testów.
STT: scripts/voice-lock.json — Whisper.cpp b5454 CPU i wielojęzyczny small.
TTS: zainstalowane głosy System.Speech z Windows (licencja Microsoft, bez
pobierania modelu TTS przez aplikację). Jest to wstępny profil etapu 2.
OCR/VLM mają manifest vision-lock.json; embedding dostanie osobny manifest w etapie 2.5b.

Etap 2.5a: Pillow 13.0.0, pypdfium2 5.14.0, Qwen3-VL-4B-Instruct Q4_K_M Unsloth + mmproj F16. Szczegóły i SHA: scripts/vision-lock.json i vendor-lock.json. Profil Windows/CUDA wymaga pomiaru.

UI: Marked 17.0.5 MIT z lokalnej dystrybucji, web/vendor/marked, SHA scripts/web-vendor-lock.json. Bez CDN. Podstawowy TeX renderowany własnym ograniczonym parserem do natywnego MathML.

Budżet odpowiedzi od 02.11: 2048 tokenów tekst/VLM, kontekst nadal 4096; tekst wejściowy i historia ograniczane tokenizerem. Nie zwiększano alokacji KV przez zmianę ctx-size. Natywny pomiar GPU niewykonany.

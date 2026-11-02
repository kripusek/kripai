# Zależności dostarczone w paczce

Python pochodzi z python.org; jego licencja jest w oryginalnym ZIP.
Biblioteki w vendor/ są niezmienionymi kołami PyPI, zawierającymi metadane
i licencje upstream. Lista wersji: requirements.lock; SHA: scripts/vendor-lock.json.

llama.cpp, CUDA DLL i model są pobierane z oficjalnych źródeł opisanych
w docs/ZRODLA.md. Licencja modelu: Apache-2.0 według repozytorium Qwen.
DLL NVIDIA i runtime Microsoft mają własne warunki upstream.

Etap 2: whisper.cpp b5454 i model Whisper small na licencji MIT. Kopie licencji:
docs/licenses/whisper-cpp-LICENSE.txt oraz whisper-model-LICENSE.txt.
System.Speech oraz zainstalowane głosy Microsoft są składnikami Windows na
warunkach Microsoft; aplikacja ich nie redystrybuuje. TTS nie jest modelem
open source. Nie używamy usług głosowych w chmurze.

Etap 2.5a: Pillow 13.0.0 (MIT-CMU) i pypdfium2 5.14.0 (BSD-3-Clause/Apache-2.0 i licencje komponentów PDFium). Oryginalne wheels wraz z licencjami w vendor. Qwen3-VL-4B-Instruct, kwantyzacja Unsloth: Apache-2.0, pobierany osobno, nie w ZIP.

Marked 17.0.5, MIT. Oryginalna dystrybucja marked.umd.js i LICENSE.md w web/vendor/marked, skopiowane z już dostępnego lokalnego pakietu. Nie pobierano nowych bibliotek.

Repozytorium nie zawiera binarnego vendor; pełna paczka ZIP zachowuje wheels
i ich oryginalne licencje. START pobiera brakujące dokładnie te same pliki
z weryfikacją przypiętego SHA, bez zmiany wersji. web/syntax.js jest własnym
lekkim lexerem projektu, bez nowej biblioteki i bez CDN.

Etap 2.5b: sqlite-vec 0.1.6 (MIT lub Apache-2.0), kopie licencji upstream
w docs/licenses/sqlite-vec-LICENSE-*.txt. Wheel Windows i DLL przypięte przez SHA.
Linux SO do QA ma osobny przypięty SHA. Model intfloat/multilingual-e5-small
(MIT), kwantyzacja GGUF cstr Q8_0, pobierany osobno; nie redystrybuowany w Git.
Model bazowy: https://huggingface.co/intfloat/multilingual-e5-small
Konwersja: https://huggingface.co/cstr/multilingual-e5-small-GGUF

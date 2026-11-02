# Oficjalne źródła sprawdzone 30.10.2026
- Python Windows / prywatna dystrybucja i vendoring: https://docs.python.org/3/using/windows.html
- Python 3.13.17: https://www.python.org/downloads/release/python-31317/
- Python ZIP: https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip
  SHA256: 9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38
- llama.cpp wydanie i SHA assetów: https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b12000
- llama.cpp flags/API/tokenizer: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Windows Job Objects: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- Microsoft VC runtime: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
- SQLite backup API w Python: https://docs.python.org/3/library/sqlite3.html
- Model/revision: https://huggingface.co/Qwen/Qwen3-8B-GGUF
- sqlite-vec plan: https://alexgarcia.xyz/sqlite-vec/python.html
  https://alexgarcia.xyz/sqlite-vec/features/vec0.html

Wersje wheels ustalono z metadanych PyPI i pobrano koła win_amd64/cp313 lub
pure Python. Dokładny lock i SHA w scripts/vendor-lock.json. Nie używamy pip
na komputerze właściciela; aplikacja dostarcza własne biblioteki.
Samo istnienie flag i pakietów w dokumentacji nie zastępuje testu Windows/CUDA.

## Etap 2 — sprawdzono 30.10.2026
- Oficjalne wydanie/manifest SHA Windows CPU b5454:
  https://api.github.com/repos/ggml-org/whisper.cpp/releases/tags/b5454
- Flagi CLI w kodzie przypiętego wydania (model, file, language, threads,
  no-gpu, output-txt, output-file):
  https://github.com/ggml-org/whisper.cpp/blob/b5454/examples/cli/cli.cpp
- Model wielojęzyczny i metadane SHA:
  https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1
- System.Speech, głosy dostępne przez GetInstalledVoices i wybór SelectVoice:
  https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.getinstalledvoices
  https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.selectvoice
  https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.setoutputtowavefile
- Mikrofon/zgoda/localhost oraz AudioWorklet:
  https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
  https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet

URL i SHA dostaw opisuje scripts/voice-lock.json. Binaria Windows rozpakowano
i sprawdzono SHA/obecność whisper-cli.exe oraz DLL; nie wykonano ich na Linux.
Dodatkowa próba prawdziwego STT użyła oficjalnego Linux b5454 z SHA
a72becf15d7917f990f6313867a52638b82b7f9ef237fb0c980dac56a135781c
i przykładu samples/jfk.wav z tego wydania. To próba EN, nie benchmark PL.

Korekta STT: ggml-small.bin, 487601967 bajtów, SHA256
1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b.
Metadane przypiętej rewizji sprawdzono bezpośrednio w oficjalnym API Hugging Face;
pobrany plik przeszedł weryfikację SHA. Rozmiary i profile modeli:
https://github.com/openai/whisper#available-models-and-languages
Nie wyciągamy z testu EN wniosku o dokładności konkretnego nagrania PL.

Etap 2.5a — ponownie zweryfikowano metadane upstream 30.10.2026:
https://pypi.org/pypi/Pillow/13.0.0/json
https://pypi.org/pypi/pypdfium2/5.14.0/json
https://huggingface.co/unsloth/Qwen3-VL-4B-Instruct-GGUF/tree/00c00da0690c4b14b5539b02c4ea5d7c9102b35e
https://github.com/ggml-org/llama.cpp/blob/b12000/tools/server/README.md
API Pillow/PDFium sprawdzone w źródłach i docstringach przypiętych wheels oraz rzeczywistym dekodowaniu. Flagi mmproj/no-mmproj-offload/image-max-tokens potwierdzone README serwera b12000.
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information
Job Object: limit ProcessMemory + JOB_OBJECT_LIMIT_PROCESS_MEMORY (0x100), nie sandbox. Natywny test limitu dodany; na Linux pominięty.

02.11.2026: wersja i API Marked sprawdzone w lokalnej oficjalnej dystrybucji (package.json, README, lib/marked.umd.js). README ostrzega, że wynik HTML wymaga sanitizacji; nasz renderer nie używa wyniku HTML, tylko tokenów i jawnie tworzonych węzłów DOM. Wcześniejszą blokadę pobierania bibliotek z internetu zachowano; użyto lokalnej dystrybucji.

02.11.2026 — bootstrap brakujących wheels z repo: oficjalny JSON API PyPI,
GET /pypi/<project>/<version>/json, pole urls, filename, digests.sha256 i url.
https://docs.pypi.org/api/json/
Adres koła dopuszczony tylko HTTPS files.pythonhosted.org/packages/, hash
i nazwa muszą zgadzać się z lokalnym vendor-lock.json. Odczyt dokumentacji
nie jest testem rzeczywistego pobierania całej paczki na Windows.

## RAG — sprawdzono 02.11.2026
https://alexgarcia.xyz/sqlite-vec/python.html
https://alexgarcia.xyz/sqlite-vec/features/vec0.html
https://github.com/asg017/sqlite-vec/releases/tag/v0.1.6
https://pypi.org/pypi/sqlite-vec/0.1.6/json
https://huggingface.co/intfloat/multilingual-e5-small
https://huggingface.co/intfloat/multilingual-e5-small/raw/main/config.json
https://huggingface.co/cstr/multilingual-e5-small-GGUF
https://raw.githubusercontent.com/ggml-org/llama.cpp/b12000/tools/server/README.md
https://raw.githubusercontent.com/ggml-org/llama.cpp/b12000/src/models/bert.cpp
https://raw.githubusercontent.com/ggml-org/llama.cpp/b12000/src/llama-arch.cpp
Pobrano i zweryfikowano Windows/Linux wheels, DLL/SO i E5 Q8_0; hash w lockach.
Jawny override tokenizer.ggml.token_type_count=int:2 wynika z config type_vocab_size
i loadera b12000. Poprawność obu partycji vec0 i runtime E5 potwierdzono na Linux.
Nie uznano dokumentacji upstream za test Windows.

## Narzędzia odczytu 4a — 02.11.2026
https://raw.githubusercontent.com/ggml-org/llama.cpp/b12000/docs/function-calling.md
https://raw.githubusercontent.com/ggml-org/llama.cpp/b12000/tools/server/README.md
https://docs.github.com/en/rest/repos/contents
https://docs.github.com/en/rest/issues/issues#list-repository-issues
https://docs.github.com/en/rest/search/search#search-repositories
https://docs.python.org/3/library/http.client.html
Włączono --jinja w tekstowym profilu; model i VRAM bez zmiany profilu.
Publiczne GitHub API, bez tokenów. Własny adapter HTTPS przypina sprawdzone IP
z TLS SNI i walidacją nazwy; testy kontrolowane. Rzeczywisty DNS hosta QA
odmówił odczytu api.github.com; nie jest to potwierdzenie sieci na Windows.

## Duże strony / wyszukiwanie — 02.11.2026
https://docs.python.org/3/library/zlib.html
https://docs.python.org/3/library/html.parser.html
https://docs.python.org/3/library/xml.etree.elementtree.html
https://www.bing.com/search?format=rss&q=Python+documentation
Sprawdzono rzeczywisty kanał RSS (5 wyników) i większy HTML przez urllib QA.
Publiczny RSS Bing służy osobistemu agregowaniu; obowiązują warunki operatora,
nie traktować go jako gwarantowanego API dla dowolnego wdrożenia.
Witryna https://our-website-is-broken.org zwracała Site Unavailable w tej próbie.
Nie uznano tej odpowiedzi za odczyt jej właściwej treści.

## Integracje 4c
https://docs.github.com/en/rest/repos/contents
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata

## Pierwszy zapis GitHub (4d)
https://docs.github.com/en/rest/git/trees#create-a-tree
https://docs.github.com/en/rest/git/commits#create-a-commit
https://docs.github.com/en/rest/git/refs#create-a-reference
https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request

## Kreator GitHub
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

## Odmowy i limity GitHub REST
https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api

## Kopie dziennika SQLite
https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
https://www.sqlite.org/backup.html

## MCP stdio (protokół 2025-11-25)
https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
https://modelcontextprotocol.io/specification/2025-11-25/server/tools
https://pypi.org/project/mcp/2.3.0/ (SDK wyłącznie QA, brak nowej zależności runtime)

## Wyszukiwanie modułów Pythona
https://docs.python.org/3/py-modindex.html
https://docs.python.org/3/library/pathlib.html

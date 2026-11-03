# Pamięć obrazów — wykonane próby 03.11.2026

Środowisko: Windows, prywatny CPython 3.13.17, SQLite 3.50.4,
rzeczywisty sqlite-vec i procesy Windows Job Object. To nie jest wynik Linux.

- Pełny Python: 386 testów, 385 OK, 1 pominięty (konto Windows nie może
  utworzyć symlinku); junction NTFS sprawdzony. Zestaw wykonany ponownie po
  poprawce atomowego sygnału startu i limitu opisu — wynik końcowy poniżej.
- Node: 189/189 OK, w tym zgodność rzeczywistego HTML z kontrolkami, obie drogi
  otwarcia panelu, wybór do5, CSRF, brak autosend/VLM, Gaming, stare odpowiedzi
  po logout, błędy i brak ponownego hashowania instalacji podczas pollingu.
- Instalator: 14 testów z realnymi folderami NTFS, kontrolowane pobrania;
  atrap wheels nie wykonywano. Zła suma, przekierowanie poza allowlistę,
  anulowanie podczas pobrania/blokady, zip traversal/budżet, zachowanie obcych
  plików, zachowanie poprzedniej instalacji i rollback promocji.
- Rzeczywisty instalator HTTPS: 6 assets +21 wheels, 25,516s,
  1976 plików/526458449B, verifyTRUE. Bez tokenów i kont. Runtime w izolowanym
  katalogu QA, nie jest to jeszcze potwierdzenie instalacji właściciela.
- Indeks: rzeczywisty SQLite/vec0 i dekodery PNG/JPEG/PDF; inference w tych
  testach jednostkowych to jawna atrapa. 768d, checkpoint, wznowienie bez
  duplikatów, ACL przed KNN, obcy owner/dokument/space, spóźniony zapis po
  pause/rebuild/usunięciu/logout/Gaming, quota i rollback, kopia/restore/delete,
  odmowa publikacji niespójnej kopii i migracja7→8 z kopią przed zmianą.
- Rzeczywisty ONNX CPU: jawny CPUExecutionProvider,2wątki, nie llama/GPU.
  6 syntetycznych ilustracji, 12 opisów PL/EN: top1 12/12. Startup2,503s,
  obrazy0,156–0,206s, opisy0,053–0,106s, całość4,531s. PeakWS611827712B,
  private934453248B, peakcommit1026715648B. Dziecko zamknięte po zadaniu.
  To pomiar małej próby, bez twierdzenia o ogólnej jakości zdjęć lub OCR.
- Chromium + rzeczywiste API/CPU/SQLite: upload3PNG i3-stronicowego PDF,
  indeks wszystkich4plików, wyszukiwanie polskiego opisu zielonego trójkąta,
  poprawny wynik. Osobna próba tylkoPDF dała top1 stronę3, przycisk naprawdę
  otworzył stronę3 przez dekoder. Opis400znaków przekraczający64tokeny daje
  czytelny błąd zamiast cichego obcięcia. Mobile390: brak overflow dokumentu
  i dialogu. Logout czyści opis/wyniki. Brak wyjątków JS, POSTmessages0,
  POSTanalyze0, inference LLM0. Początkowe401 przed loginem i celowe422 zbyt
  długiego zapytania są oczekiwanymi odpowiedziami HTTP.

Wykryte i naprawione: brakujące przyciski w HTML (atrapa DOM sama je tworzyła),
utracone polskie znaki nowego dialogu, nieatomowy zapis ready.json oraz
kosztowne hashowanie instalacji przy każdym odświeżeniu postępu. Dodano testy
markup/statusrequestcount. Pierwszy skrypt QA wybrał plik zanim panel zakończył
odczyt listy; poprawiono oczekiwanie skryptu, bez zmiany zachowania uploadu.

NIE URUCHOMIONO dla tej paczki: nowa inference CUDA, mikrofon/PL–EN głosu,
prywatne konto GitHuba, dane/zdjęcia właściciela, ogólny benchmark fotografii.
Konto, baza i kontroler rozmowy w Chromium były testowe; encoder i dekoder
były rzeczywiste. Nie zaliczamy tym szerszych etapów3/5/6.

Końcowy pełny przebieg po poprawkach: 386 Python w217,412s, OK(skipped=1);
Node189/189. Rzeczywisty transport z przypiętym runtime: opisPL→3072B,
400znaków/>64tokeny→visual_query_too_large, przerwanie kontekstu zamknęło
żywy proces w0,033s; pełne verify instalacji po procesie nadalTRUE.

Potwierdzenie instalacji480a429: wykonano kopię kodu i SQLite przed aktualizacją;
backend wystartował z migracją8, source/install/running fingerprint zgodne.
Przygotowany runtime skopiowano do własnego nowego katalogu w program/runtime,
zweryfikowano pełny inwentarz. Zainstalowany proces CPU rzeczywiście zakodował
PNG i opis do3072B i zakończył się po zadaniu. Health200, dokładne pliki
HTML/JS, visual/status i search bez sesji401. Nie logowano konta właściciela;
nie uruchamiano nowej inferenceCUDA. Wcześniejsze testy interfejsu pozostają
testami na izolowanej bazie/kontrolerze, co opisano wyżej.

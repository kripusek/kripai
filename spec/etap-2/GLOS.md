# Etap 2 — wstępny moduł głosu, Windows native

Zakres rozpoczęty na polecenie właściciela: lokalny głos w Web UI.
Brak zmian schematu historii i brak implementacji etapów 2.5–6.

## Przepływ
Nagraj → zgoda przeglądarki → mikrofon → AudioWorklet → konwersja do PCM16
mono 16 kHz przez OfflineAudioContext → uwierzytelnione API → whisper-cli CPU
→ tekst w polu wiadomości → właściciel poprawia i klika Wyślij.
Kliknięcie Czytaj → prywatny plik JSON → Windows PowerShell System.Speech
→ WAV → odtwarzacz przeglądarki. Tekst jest przekazywany przez Speak, nie SSML.

## Profil próbny
- Whisper.cpp b5454, oficjalna paczka CPU x64, model small wielojęzyczny MIT.
  URL/rewizje/SHA w scripts/voice-lock.json; 4 wątki, --no-gpu.
- TTS: lokalne głosy Microsoft dostępne przez System.Speech. Brak zależności
  od browser SpeechRecognition/speechSynthesis lub chmurowego API.
  Brak głosu PL/EN to jawny błąd, bez podstawiania innego języka.
- TTS nie jest otwartym modelem: obowiązuje licencja Windows. Ewentualny
  otwarty silnik TTS należy dobrać po testach jakości i zasobów na Windows.
- Wyboru small ani System.Speech nie uznajemy za ostateczny profil wydajności.

## Limity i prywatność
Nagranie 0,25–30 s, dokładnie walidowany WAV do 960044 bajtów. Nie przyjmujemy
MP3/WebM ani dowolnych plików. Transcript do 4000 znaków, nie trafia do bazy
przed świadomym wysłaniem przez właściciela. TTS do 1200 znaków/żądanie;
panel dzieli odpowiedź do 12000 znaków na kolejne porcje.
Jedno zadanie głosowe naraz, bez trwałej kolejki. Limit 256 identyfikatorów na
10 minut dla całego procesu. Brak auto-retry, aby nie odtworzyć starego audio.

Zadanie jest związane z sesją i losowym UUID. Cancel zapisuje znacznik nawet
przed startem; chroni przed wyścigiem upload/cancel. UI ma licznik operacji,
odrzuca spóźnione wyniki, zatrzymuje tracki i zwalnia blob URL. Wylogowanie,
Gaming, schowanie karty i wyłączenie programu przerywają głos. Zmiana Gaming
w innej karcie/utrata backendu jest widoczna w panelu przy kontroli co 3 s.

Proces potomny ma Windows Job Object kill-on-close, timeout 90 s STT/45 s TTS,
stdout/stderr wyłączone. Nie ma shell=True, treści w argv ani żądań modelu
do uruchamiania narzędzi. Co 0,1 s kontrola anulowania, sesji i Gaming.
Job Object nie jest sandboxem ani gwarancją stałego zużycia RAM.

Audio/tekst TTS chwilowo w prywatnym KripAI-data/voice-tmp, usuwane w finally;
resztki po awarii usuwane przy starcie. Backup obejmuje historię, nie nagrania
ani modele. To usuwanie plików, nie gwarantowane wymazywanie fizycznego nośnika.

## Kryterium odbioru
Na docelowym Windows: zdania PL/EN rozpoznane, tekst można poprawić, cały odczyt
działa offline, anulowanie nie dopisuje tekstu/nie odtwarza dźwięku, brak lub
odmowa mikrofonu mają czytelny błąd. Gaming/WYLACZ nie zostawiają whisper ani
PowerShell głosu. Ocenić jakość oraz zmierzyć czas i RAM na sprzęcie właściciela.
Na razie niezaliczone: Windows, mikrofon, lokalny TTS i jakość polskiego.
Rzeczywisty test Whisper CPU EN na Linux opisany w docs/WYNIKI_TESTOW.txt.

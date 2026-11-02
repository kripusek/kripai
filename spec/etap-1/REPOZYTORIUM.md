# Struktura natywnego repozytorium
app/ — backend, SQLite, auth, kontekst i właściciel procesu modelu.
web/ — statyczny interfejs serwowany przez backend.
scripts/ — instalator i operacje właściciela Windows; test_all.py uruchamia testy.
tests/ — testy zachowania, awarii, sieci SSE i lokalnych procesów.
vendor/ — przypięta prywatna dystrybucja CPython i wheels.
spec/ — plan oraz kontrakty; docs/ — źródła, licencje, wyniki.

START.cmd i WYLACZ.cmd uruchamiaj w Windows. Runtime instalowany do
LOCALAPPDATA/KripAI/runtime. Dane oraz kopie są poza repozytorium.
Migracje SQLite są transakcyjne i kontrolowane SHA. Na tym etapie jest jedna
migracja SQLite; starych migracji PostgreSQL nie wykonuje się na SQLite.
Cofanie danych: sprawdzony backup przy zatrzymanej aplikacji. Nie używać
narzędzi migrate.py z poprzedniej paczki WSL. Pełny plan: ../06-rollout.md.

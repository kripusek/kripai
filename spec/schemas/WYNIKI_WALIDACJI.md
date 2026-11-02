# Wyniki walidacji — aktualny pakiet

- `PYTHONPATH=/tmp/verification_deps python3 final_nowe/tests/validate.py` → `PASS schema: 29 WSS + 1 REST + 1 payload; negative schema: 22 ; testy semantyki/firmware NIE URUCHOMIONO`. Narzędzie jsonschema 4.26.0 oraz FormatChecker i rozszerzenie x-maxUtf8Bytes.
- OpenAPI 3.1: openapi-spec-validator 0.9.0 → `final_nowe/etap-1/openapi.yaml: OK`.
- SQL: pglast 8.7 → `pglast v8.7 statements 10`. To wyłącznie parser. PostgreSQL test FK i rollback NIE URUCHOMIONO; przyczyna w WERYFIKACJA.md.
- Compose: NIE URUCHOMIONO docker compose config (brak Docker).
- Testy zachowania urządzenia, kryptografii, modeli, wymogów użytkownika i pełnej spójności wszystkich pól/enumów: NIE URUCHOMIONO. Policy examples z wcześniejszej wersji nie były testami systemu i nie są częścią aktualnego validate.py.

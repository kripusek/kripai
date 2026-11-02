"""Hasła i tokeny: bez przechowywania jawnych sekretów w bazie."""
import hashlib
import hmac
import secrets


def digest(token):
    return hashlib.sha256(token.encode()).digest()


def password_hash(password):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$16384$8$1$' + salt.hex() + '$' + key.hex()


def verify_password(password, encoded):
    try:
        name, n, r, p, salt, expected = encoded.split('$')
        if name != 'scrypt' or (n, r, p) != ('16384', '8', '1'):
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False

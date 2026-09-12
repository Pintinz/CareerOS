from passlib.context import CryptContext

# Argon2 per master spec §69 (Argon2/Bcrypt). Never store or log plaintext passwords.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)

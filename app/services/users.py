from dataclasses import dataclass


def _hash_password(password: str) -> str:
    import hashlib

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class User:
    username: str
    full_name: str
    role: str
    password_hash: str


USERS_DB: dict[str, User] = {
    "tony": User("tony", "Tony Stark", "engineering", _hash_password("password123")),
    "bruce": User("bruce", "Bruce Wayne", "marketing", _hash_password("securepass")),
    "sam": User("sam", "Sam Wilson", "finance", _hash_password("financepass")),
    "natasha": User("natasha", "Natasha Romanoff", "hr", _hash_password("hrpass123")),
    "steve": User("steve", "Steve Rogers", "employee", _hash_password("employeepass")),
    "pepper": User("pepper", "Pepper Potts", "executive", _hash_password("executivepass")),
}


def get_user(username: str | None) -> User | None:
    if not username:
        return None
    return USERS_DB.get(username.strip().lower())


def list_demo_users() -> list[dict[str, str]]:
    return [
        {"username": user.username, "full_name": user.full_name, "role": user.role}
        for user in USERS_DB.values()
    ]

from typing import Iterable


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "employee": {"general"},
    "general": {"general"},
    "finance": {"general", "finance"},
    "marketing": {"general", "marketing"},
    "hr": {"general", "hr"},
    "engineering": {"general", "engineering"},
    "executive": {"general", "finance", "marketing", "hr", "engineering"},
}

ROLE_LABELS: dict[str, str] = {
    "employee": "Employee",
    "general": "Employee",
    "finance": "Finance Team",
    "marketing": "Marketing Team",
    "hr": "HR Team",
    "engineering": "Engineering Department",
    "executive": "C-Level Executive",
}


def normalize_role(role: str) -> str:
    return role.strip().lower().replace(" ", "_").replace("-", "_")


def allowed_departments_for(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(normalize_role(role), {"general"})


def role_can_access_department(role: str, department: str) -> bool:
    return department in allowed_departments_for(role)


def allowed_roles_for_department(department: str) -> list[str]:
    department = department.lower()
    return sorted(
        role
        for role, departments in ROLE_PERMISSIONS.items()
        if department in departments and role != "general"
    )


def format_departments(departments: Iterable[str]) -> str:
    return ", ".join(sorted(departments))

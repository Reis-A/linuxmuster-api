from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import json

def extract_schoolname(dn: str) -> str | None:
    dn_lower = dn.lower()

    start_key = "ou=benutzer,"
    end_key = ",ou=schulen"

    start_index = dn_lower.find(start_key)
    if start_index == -1:
        return None

    start_index += len(start_key)

    end_index = dn_lower.find(end_key, start_index)
    if end_index == -1:
        return None

    # Extract from the ORIGINAL DN to preserve casing
    segment = dn[start_index:end_index].strip()

    # segment is "ou=SchoolName"
    if segment.lower().startswith("ou="):
        return segment[3:]  # remove "ou="

    return None

def extract_role_ou(dn: str) -> str | None:
    # Split DN into parts
    parts = [p.strip() for p in dn.split(",")]

    # Normalize to lowercase for comparison
    parts_lower = [p.lower() for p in parts]

    # Find index of ou=benutzer
    try:
        idx = parts_lower.index("ou=benutzer")
    except ValueError:
        return None

    # The role OU is the part directly before ou=benutzer
    if idx == 0:
        return None  # nothing before it

    role_part = parts[idx - 1]  # original casing preserved

    # Expecting something like "ou=Lehrer"
    if role_part.lower().startswith("ou="):
        return role_part[3:]  # remove "ou="

    return None


def map_role_to_sophomorix(role_ou: str | None, dn: str) -> str | None:
    dn_lower = dn.lower()
    if ( "cn=admin" in dn_lower and "ou=server" in dn_lower and "ou=dienste" in dn_lower ):
        return "globaladministrator"
# 2. Normal school roles if role_ou is None: return None


    if role_ou is None:
        return None

    r = role_ou.lower()

    if r in ("lehrer", "teacher"):
        return "teacher"
    if r in ("schueler", "student"):
        return "student"
    if r in ("verwalter", ""):
        return "schooladministrator"
    if r in ("pruefungen"):
        return "examuser"
    return "unknown"



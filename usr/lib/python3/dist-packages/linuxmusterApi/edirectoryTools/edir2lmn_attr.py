from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import json



def extractLehrerliste(members):
    lehrerlist= [x for x in members if "ou=lehrer" in x.lower()] 
    return [x.split(',')[0][3:].lower() for x in lehrerlist]
def extract_schoolname(dn: str) -> str | None:
    parts = [p.strip() for p in dn.split(",")]

    # Normalize to lowercase for comparison
    parts_lower = [p.lower() for p in parts]
    # Find index of ou=benutzer
    try:
        idx = parts_lower.index("ou=schulen")
    except ValueError:
        return "global"
    # The role OU is the part directly before ou=schulen
    if idx == 0:
        return None  # nothing before it
    if parts_lower[idx - 1].startswith("ou="):
      return parts_lower[idx - 1][3:]  # remove ou= return lowercase

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
    if ( "ou=global" in dn_lower and "o=ml3" in dn_lower ):
        return "globaladministrator"
# 2. Normal school roles if role_ou is None: return None


    if role_ou is None:
        return None

    r = role_ou.lower()

    if r in ("lehrer"):
        return "teacher"
    if r in ("schueler"):
        return "student"
    if r in ("verwalter", ""):
        return "schooladministrator"
    if r in ("pruefungen"):
        return "examuser"
    return "unknown"



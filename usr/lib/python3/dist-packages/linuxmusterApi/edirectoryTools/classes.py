from ldap3 import Server, Connection, ALL, NTLM, SUBTREE


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
    dn_lower = dn.lower()
    key = "ou=benutzer"

    # Find "ou=benutzer"
    idx = dn_lower.find(key)
    if idx == -1:
        return None

    # Look left of it to find the previous comma
    before = dn.rfind(",", 0, idx)
    if before == -1:
        return None

    # Extract the segment between the comma and "ou=benutzer"
    segment = dn[before+1:idx].strip()

    # segment is now "ou=Lehrer" or "ou=Schueler" etc.
    if segment.lower().startswith("ou="):
        return segment[3:]  # remove "ou="
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



class EDirectoryConnector:
    def __init__(self, config):
        self.server = Server(
            config["server"],
            get_info=ALL,
            use_ssl=True,
            port=636
        )
        self.bind_dn = config["bind_dn"]
        self.bind_password = config["bind_password"]
        self.user_base = config["user_base_dn"]
        self.group_base = config["group_base_dn"]
        self.user_filter = config["user_filter"]
        self.group_filter = config["group_filter"]

        self.conn = Connection(
            self.server,
            user=self.bind_dn,
            password=self.bind_password,
            auto_bind=True
        )
    def get_user(self, username):
        search_filter = self.user_filter.format(username=username)
        self.conn.search(
            search_base=self.user_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["uid", "cn", "sn", "givenName", "mail"]
        )
        if not self.conn.entries:
            return None
        entry = self.conn.entries[0]

        # Convert to dict
        data = json.loads(entry.entry_to_json())

        # Add DN manually
        data["dn"] = entry.entry_dn
        data["sophomorixSchoolname"] = extract_schoolname(dn)
        role_ou = extract_role_ou(dn) 
        data["sophomorixRole"] = map_role_to_sophomorix(role_ou, dn)
        return data


    def get_group(self, groupname):
        search_filter = self.group_filter.format(groupname=groupname)
        self.conn.search(
            search_base=self.group_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=["cn", "description", "groupMembership"]
        )
        if not self.conn.entries:
            return None
        return self.conn.entries[0].entry_to_json()

    def list_users(self):
        self.conn.search(
            search_base=self.user_base,
            search_filter="(objectClass=inetOrgPerson)",
            search_scope=SUBTREE,
            attributes=["uid", "cn", "sn", "mail"]
        )
        return [e.entry_to_json() for e in self.conn.entries]

    def list_groups(self):
        self.conn.search(
            search_base=self.group_base,
            search_filter="(objectClass=groupOfNames)",
            search_scope=SUBTREE,
            attributes=["cn", "description"]
        )
        return [e.entry_to_json() for e in self.conn.entries]

    def get(self, path):
      parts = path.strip("/").split("/")
      if len(parts) != 2:
        raise ValueError(f"Invalid LDAP path: {path}")
      
      category, name = parts
      print(name)
      if category == "users":
          return self.get_user(name)

      if category == "groups":
          return self.get_group(name)

      raise ValueError(f"Unknown LDAP category: {category}")


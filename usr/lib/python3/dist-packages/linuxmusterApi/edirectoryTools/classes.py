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

class LMNLDAPUser:
    def __init__(self, data: dict,edirectoryConnector):
        self.data=data
        self.connector=edirectoryConnector
        for key, value in data.items():
            setattr(self, key, value)

    def test_password(self, password: str) -> bool: 
        # eDirectory requires LDAPS for password bind 
       # server = Server(self.config["server"], use_ssl=True) 
        
        
        conn = Connection(self.connector.server, user=self.data["dn"], password=password, auto_bind=False)  
        try: 
            return conn.bind()
        except ldap3.core.exceptions.LDAPBindError: 
            return False


class EDirectoryConnector:
    def __init__(self, config):
        self.config=config
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
        #attribute extrahieren
        attrs = entry.entry_attributes_as_dict
        # Werte vereinfachen (Listen → einzelne Werte)
        data = {k: v[0] if isinstance(v, list) else v for k, v in attrs.items()}
        # Convert to dict
#        data = json.loads(entry.entry_to_json())

        # Add DN manually
        dn=entry.entry_dn
        data["dn"] = entry.entry_dn
        data["distinguishedName"] = dn
        data["sophomorixSchoolname"] = extract_schoolname(dn)
        role_ou = extract_role_ou(dn) 
        data["sophomorixRole"] = map_role_to_sophomorix(role_ou, dn)
        return LMNLDAPUser(data, self)

    




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



    def getvalues_user(self, username, attrs):
       # Load the user via your existing LDAP lookup
      user_obj = self.get_user(username)
      if user_obj is None:
        raise ValueError(f"User '{username}' not found")

      # user_obj.data contains all attributes from LDAP + sophomorix extras
      #Attribute muessen im userobject gepflegt und implementiert werden in der getuser Funktion
      data = user_obj.data

      result = {}
      for attr in attrs:
          value = data.get(attr)

      return result



    def get(self, path, dict=False):
      parts = path.strip("/").split("/")
      if len(parts) != 2:
        raise ValueError(f"Invalid LDAP path: {path}")
      
      category, name = parts
      #print(name)
      if category == "users":
          return self.get_user(name)

      if category == "groups":
          return self.get_group(name)

      raise ValueError(f"Unknown LDAP category: {category}")

    def getvalues(self, path, attrs):
      parts = path.strip("/").split("/")
      if len(parts) != 2:
        raise ValueError(f"Invalid LDAP path: {path}")

      category, name = parts

      if category == "users":
        return self.getvalues_user(name, attrs)

      raise ValueError(f"Unknown LDAP category: {category}")


    def getval(self, path, attr):
      result = self.getvalues(path, [attr])
      return result[attr]


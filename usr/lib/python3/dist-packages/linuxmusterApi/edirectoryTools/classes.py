from ldap3 import Server, Connection, ALL, NTLM, SUBTREE

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
        return self.conn.entries[0].entry_to_json()

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


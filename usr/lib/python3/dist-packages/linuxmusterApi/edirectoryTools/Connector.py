from ldap3 import Server, Connection, Tls, ALL, NTLM, SUBTREE
import ssl
import json
from edirectoryTools.edir2lmn_attr import *
from .userManager import UserManager

from pydantic import BaseModel







class EDirectoryConnector:
    def __init__(self, config):
        self.config = config

        # LDAP Server
        tls_config= Tls(ca_certs_file=config["ca_cert_file"],validate=ssl.CERT_REQUIRED,version=ssl.PROTOCOL_TLS_CLIENT,ciphers='ALL') #cipers=ALL can be removed once OES 25.4 is running
        self.server = Server(
            config["server"],
            get_info=ALL,
            tls=tls_config
        )

        # Bind Credentials
        self.bind_dn = config["bind_dn"]
        self.bind_password = config["bind_password"]

        # Base DNs
        self.user_base = config["user_base_dn"]
        self.group_base = config["group_base_dn"]

        # Filters
        self.user_filter = config["user_filter"]
        self.group_filter = config["group_filter"]
        self.excluded_schools = config["excluded_schools"]
        # LDAP Connection
        self.conn = Connection(
            self.server,
            user=self.bind_dn,
            password=self.bind_password,
            auto_bind=True
        )

        # RAM‑Cache initialisieren
        self.user_manager = UserManager.instance(self)



    # ---------------------------------------------------------
    # USER-FUNKTIONEN (jetzt RAM‑Cache statt LDAP)
    # ---------------------------------------------------------

    def get_user(self, username):
        """Liefert LMNLDAPUser aus dem RAM‑Cache."""
        return self.user_manager.get_user(username)



    def getvalues_user(self, username, attrs):
        """Liefert bestimmte Attribute eines Users aus dem RAM‑Cache."""
        return self.user_manager.getvalues_user(username, attrs)



    def list_users(self):
        """Liste aller User aus dem RAM‑Cache."""
        return [u.asdict() for u in self.user_manager.list_users()]



    # ---------------------------------------------------------
    # GRUPPEN (noch direkt LDAP – kann später auch gecacht werden)
    # ---------------------------------------------------------
    ''' 
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



    def list_groups(self):
        self.conn.search(
            search_base=self.group_base,
            search_filter="(objectClass=groupOfNames)",
            search_scope=SUBTREE,
            attributes=["cn", "description"]
        )
        return [e.entry_to_json() for e in self.conn.entries]
    '''   
 
    # ---------------------------------------------------------
    # SCHOOLS ()
    # ---------------------------------------------------------
    def get_schools(self):
        return self.user_manager.get_schools()

    
    # ---------------------------------------------------------
    # SCHOOLCLASSES ()
    # ---------------------------------------------------------
    def get_schoolclasses(self,school: str | None):
        return self.user_manager.get_schoolclasses(school)
    def get_schoolclass(self,schoolclass: str, school: str | None):
        return self.user_manager.get_schoolclass(schoolclass, school)

    # ---------------------------------------------------------
    # PROJECTS ()
    # ---------------------------------------------------------
    def get_projects(self,school: str | None):
        return self.user_manager.get_projects(school)
    # ---------------------------------------------------------
    # GENERISCHE GET-FUNKTIONEN (nutzen automatisch Cache)
    # ---------------------------------------------------------

    def get(self, path, school: str | None = None, dict: bool = False):
        parts = path.strip("/").split("/")
        if len(parts) ==1:
           category= parts[0]
           if category == "schools":
             return  self.get_schools()
           if category == "schoolclasses":
             return self.get_schoolclasses(school)#schoolspecifresults #globaladmin in school global
           if category == "projects":
               return self.get_projects(school) 


        if len(parts) == 2:

           category, name = parts

           if category == "users":
              return self.get_user(name)

          # if category == "groups":
           #   return self.get_group(name)
           if category == "schools":
              return self.get_school(name)
           if category == "schoolclasses":
              return self.get_schoolclass(name,school)

        
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


from ldap3 import Server, Connection, ALL, NTLM, SUBTREE, LEVEL
from edirectoryTools.edir2lmn_attr import *
from .pydanticmodels import LMNLDAPUser, LMNSchoolClassModel
import time
from threading import Lock

class UserManager:
    _instance = None
    _lock = Lock()

    @staticmethod
    def instance(connector):
        print("UserManager.instance() called. Current instance:", UserManager._instance)
        with UserManager._lock:
            if UserManager._instance is None:
                UserManager._instance = UserManager(connector)
            return UserManager._instance

    # hier das refresh_intervall einstellen fuer full sync
    def __init__(self, connector, refresh_interval=300):
        self.connector = connector
        self.refresh_interval = refresh_interval
        self.last_sync = 0
        self.users = {}   # uid → LMNLDAPUser
        self.sync()

    # -----------------------------
    # FULL SYNC FROM LDAP
    # -----------------------------
    def sync(self):
        print("UserManager: Full LDAP sync…")

        # 1. Alte Verbindung schließen
        try:
            if self.connector.conn.bound:
                self.connector.conn.unbind()
        except:
            pass

        # 2. Neue Verbindung öffnen
        self.connector.conn = Connection(
            self.connector.server,
            user=self.connector.bind_dn,
            password=self.connector.bind_password,
            auto_bind=True
        )
        
        #########Users############

        # 3. LDAP-Abfrage
        self.connector.conn.search(
            search_base=self.connector.user_base,
            search_filter=self.connector.user_filter,
            search_scope=SUBTREE,
            attributes=["uid", "cn", "sn", "givenName", "mail", "fullname","groupMembership"]
        )
    
        new_users = {}

        # 4. Einträge verarbeiten
        for entry in self.connector.conn.entries:
            dn = entry.entry_dn
            school = extract_schoolname(dn)
            cn = entry.cn.value
            groupmembership=entry.groupMembership.value or []
            adminclass,role= map_role_to_sophomorix(extract_role_ou(dn), dn)
            data = {
                "cn": cn.lower(),
                "name": cn,
                "sAMAccountName": cn.lower(),
                "mail": [entry.mail.value],
                "displayName": entry.fullname.value,
                "dn": dn,
                "distinguishedName": dn,
                "sophomorixSchoolname": school,
                "school": school,
                "sophomorixRole": role,
                "sophomorixStatus":"active",
                "memberOf": groupmembership,
                "lmnsessions":[],
                "sophomorixAdminClass": adminclass,
                "wifi": None,
                "printing": None,
                "webfilter":None,
                "internet":None,
                "permissions": {"sidebar:view:/view/lmn/users/print-passwords": False}
            }
            #management groups wifi printing webfilter internet can be used to toggle groupmembership in managementgroup endpoints 
            #right now this functions are all disabled, here and in the management route of the API

            #schoolclasses and projects attribute set in model
            # WICHTIG: Diese Zeile muss IN der Schleife stehen!
            key = cn.lower()
            new_users[key] = LMNLDAPUser(data,self.connector)

        # 5. Cache ersetzen
        self.users = new_users
        print(f"UserManager: Loaded {len(self.users)} users into RAM")
       # print(self.users)
        ###########schools##############################
        self.connector.conn.search(
            search_base="ou=schulen,o=ml3",
            search_filter="(objectClass=organizationalUnit)",
            search_scope=LEVEL,
            attributes=["ou"]
        )
        #print(self.connector.conn.entries)
        self.schools=[]
        data={} 
        for entry in self.connector.conn.entries:
            dn=entry.entry_dn
            ou = extract_schoolname(dn)            
            data={
                    "objectClass": ["organizationalUnit"],
                   "ou": ou,
                   "name": ou,
                   "distinguishedName": dn,
                   "displayName": ou
                }
            if ou not in [p.lower() for p in self.connector.excluded_schools]:
              self.schools.append(data)
        print(f"UserManager: Loaded {len(self.schools)} schools into RAM")


        #################schoolclasses################################
        self.schoolclasses={}
        for school in self.schools:
           schoolclasses=[]
        
           self.connector.conn.search(
            search_base=f"ou=klassen,ou=gemischt,ou=gruppen,ou={school['ou']},ou=schulen,o=ml3",
            search_filter="(objectClass=groupofNames)",
            search_scope=LEVEL,
            attributes=["cn","member"]
            )
          # print(self.connector.conn.entries)
           data={}
           
           for entry in self.connector.conn.entries:
               dn=entry.entry_dn
               cn=entry.cn.value
               lehrerliste=extractLehrerliste(entry.member.values)
               sophomorixMembers=[dn.split(',')[0][3:].lower() for dn in entry.member.values if dn.split(',')[0][3:].lower() not in set(lehrerliste)]

               #print(entry.member.value)
               data={
                       "objectClass":["groupofNames"],
                       "cn": cn,
                       "name": cn,
                       "displayName": cn,
                       "dn": dn,
                       "distinguishedName": dn,
                       "member": entry.member.values,
                       "membersCount": len(sophomorixMembers),
                       "sophomorixHidden": False,
                       "sophomorixJoinable": False,
                       "sophomorixType": "adminclass",
                       "sophomorixAdmins": lehrerliste,
                       "sophomorixMembers": sophomorixMembers
                       
                    }
               schoolclasses.append(data)
             #  print(schoolclasses)
           self.schoolclasses[school['ou']]=schoolclasses
 
         ##################Projects###########################
        self.projects={}
        for school in self.schools:
           projects=[]

           self.connector.conn.search(
            search_base=f"ou=projekte,ou={school['ou']},ou=schulen,o=ml3",
            search_filter="(objectClass=groupofNames)",
            search_scope=LEVEL,
            attributes=["cn","member","owner"]
            )
           print(self.connector.conn.entries)
           data={}

           for entry in self.connector.conn.entries:
               dn=entry.entry_dn
               cn=entry.cn.value
               owners = entry.owner.values if isinstance(entry.owner.values, list) else [entry.owner.value]
               #print(owners)
               ownerliste=[dn.split(',')[0][3:].lower() for dn in owners]
              # print(ownerliste)
               sophomorixMembers=[dn.split(',')[0][3:].lower() for dn in entry.owner.values if dn not in set(ownerliste)]
               #print(entry.member.value)
               data={
                       "objectClass":["groupofNames"],
                       "cn": cn,
                       "name": cn,
                       "displayName": cn,
                       "dn": dn,
                       "distinguishedName": dn,
                       "member": entry.member.values,
                       "membersCount": len(entry.member.values),
                       "sophomorixHidden": False,
                       "sophomorixJoinable": False,
                       "sophomorixType": "project",
                       "sophomorixAdmins": ownerliste, 
                       "sophomorixMembers": sophomorixMembers

                    }
               projects.append(data)
               print(data)
           self.projects[school['ou']]=projects


        self.last_sync = time.time()


    # -----------------------------
    # AUTO REFRESH
    # -----------------------------
    def ensure_fresh(self):
        if time.time() - self.last_sync > self.refresh_interval:
            self.sync()

    # -----------------------------
    # PUBLIC API
    # -----------------------------
    def get_user(self, username):
        self.ensure_fresh()
        return self.users.get(username)

    def getvalues_user(self, username, attrs):
        self.ensure_fresh()
        user = self.users.get(username)
        if not user:
            return None
        return {attr: user.data.get(attr) for attr in attrs}

    def list_users(self):
        self.ensure_fresh()
        return list(self.users.values())

    def get_schools(self):
        self.ensure_fresh()
        return self.schools
    def get_school(self, schulname):
        self.ensure_fresh()
        return next((s for s in self.schools if s["name"] == schulname), None)

    def get_schoolclasses(self,school:str | None):
        
        if school!="global":
          #  print(school)
            return self.schoolclasses[school] #dict for schools
        return list(self.schoolclasses.values())
     
    def get_schoolclass(self, schoolclass, school:str | None):
        schoolclasses= self.get_schoolclasses(school)
        result = next((item for item in schoolclasses if item["cn"] == schoolclass), None)
        print(result)
        return result

    def get_projects(self,school:str | None):
        if school!="global":
            return  self.projects[school]
        return list(self.projects.values())


from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import json
from edirectoryTools.edir2lmn_attr import *
import re
from pydantic import BaseModel
def _check_schoolclass_number(s):
        n = re.findall(r'\d+', s)
        if n:
            return int(n[0])
        else:
            return 10000000 # just a big number to come after all schoolclasses



#wird erstmal net gebraucht
class LMNSchoolClassModel(BaseModel):
    cn: str
    displayName: str
    distinguishedName: str
    member: list
    name: str
    objectClass: list
    sophomorixHidden: bool
    sophomorixJoinable: bool
    membersCount: int 
    sophomorixType: str
    dn: str 








class LMNUserModel(BaseModel):
    uid: str
    cn: str
    dn: str
    sn: str | None = None
    givenName: str | None = None
    mail: list | None = None
    sophomorixRole: str
    sophomorixSchoolname: str
    schoolclasses:  list 
    memberOf: list
    lmnsessions: list
    sophomorixStatus: str
    sophomorixAdminClass: str
    projects: list

class LMNLDAPUser:
    def __init__(self, data: dict,edirectoryConnector):
        self.data=data
        self.connector=edirectoryConnector
        membership = data.get("memberOf")
        if membership:
            data["schoolclasses"] = self.extract_schoolclasses(membership)
            data["projects"] =self.extract_projects(membership)
        for key, value in data.items():
            setattr(self, key, value)

    def asdict(self):
      result = {}
      for key, value in self.__dict__.items():
          if key in ("edirectory Connector", "data"):
              continue # normalize ldap3 lists
          if isinstance(value, list) and len(value) == 1: 
              result[key] = value[0]
          else:
              result[key] = value
      return result


     # return self.data
 
    def __iter__(self):
      yield from self.data.items()

    def __getitem__(self, item):
      return self.data[item]

    def __json__(self):
      return self.data
    def to_pydantic(self):
        return LMNUserModel(**self.data)


    def extract_schoolclasses(self, membership):
        schoolclasses = []
        for dn in membership:
            if 'ou=gemischt' in dn:
                schoolclass = dn.split(',')[0][3:]
                if schoolclass:
                    schoolclasses.append(schoolclass)
        schoolclasses = sorted(schoolclasses, key=lambda s: (_check_schoolclass_number(s), s))
        return schoolclasses
    def extract_projects(self, membership):
        projects = []
        for dn in membership:
            if 'ou=Projekte' in dn:
                project = dn.split(',')[0][3:]
                if project:
                    projects.append(project)
       # schoolclasses = sorted(schoolclasses, key=lambda s: (_check_schoolclass_number(s), s))
        return projects


    def test_password(self, password: str) -> bool: 
        # eDirectory requires LDAPS for password bind 
       # server = Server(self.config["server"], use_ssl=True) 
        
        
        conn = Connection(self.connector.server, user=self.data["dn"], password=password, auto_bind=False)  
        try: 
            return conn.bind()
        except ldap3.core.exceptions.LDAPBindError: 
            return False
    def to_pydantic(self): 
        return LMNUserModel(**self.data)







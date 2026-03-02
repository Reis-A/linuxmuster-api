from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import json
from edirectoryTools.edir2lmn_attr import *

from pydantic import BaseModel

class UserOut(BaseModel):
    uid: str
    cn: str
    dn: str
    sn: str | None = None
    givenName: str | None = None
    mail: str | None = None
    sophomorixRole: str
    sophomorixSchoolname: str



class LMNLDAPUser:
    def __init__(self, data: dict,edirectoryConnector):
        self.data=data
        self.connector=edirectoryConnector
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



    def test_password(self, password: str) -> bool: 
        # eDirectory requires LDAPS for password bind 
       # server = Server(self.config["server"], use_ssl=True) 
        
        
        conn = Connection(self.connector.server, user=self.data["dn"], password=password, auto_bind=False)  
        try: 
            return conn.bind()
        except ldap3.core.exceptions.LDAPBindError: 
            return False
    def to_pydantic(self): 
        return UserOut(**self.data)







from edirectoryTools.Connector import EDirectoryConnector
import yaml

with open('/etc/linuxmuster/api/config.yml', 'r') as config_file:
    config = yaml.load(config_file, Loader=yaml.SafeLoader)

lr = EDirectoryConnector(config["ldap"])


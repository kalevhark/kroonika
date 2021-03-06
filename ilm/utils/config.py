#!/home/ec2-user/django/kroonika_env/bin/python3
import os
from configparser import ConfigParser

# The following config() function read the database.ini file and returns the connection parameters.
def config(path='', filename='utils/database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(os.path.join(path, filename))

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db

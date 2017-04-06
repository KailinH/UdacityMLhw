from ._controller import ModelControllerFactory as _controller
from swt.schema.models.user import UserLdap, UserSwt, User
from flask import g
import requests
from swt.exceptions.api_expections import ApiPreconditionFailedException, ApiSqlException

def get_users_swt(usernames):
    conn = g._db

    with conn.cursor() as cursor:

        """
        Get List of DIGS facilities with the required technology
        """
        users = []
        cursor.execute("SELECT * FROM Users WHERE `username` IN ()".format(usernames))
        columns = [field[0] for field in cursor.description]
        user = UserSwt()

        for row in cursor:
            users.append({k:v for k, v in zip(columns, row)})
        cursor.close()

    return users

def get_user_swt(username):
    conn = g._db

    with conn.cursor() as cursor:

        """
        Get List of DIGS facilities with the required technology
        """

        cursor.execute("SELECT * FROM Users WHERE `username` LIKE \"{}\"".format(username))
        columns = [field[0] for field in cursor.description]
        user = UserSwt()

        for row in cursor:
            for k, v in zip(columns, row):
                setattr(user, k, v)
        cursor.close()

    #conn.close()

    return user.__dict__


def get_user_ldap(username, config):
    #user = UserLdap()
    ldap_url = config.get('ldap', 'url')
    r = requests.get(ldap_url + username, timeout=2)
    rj = r.json()
    if "status" in rj:
        if not rj["status"]:
            return {}

    return {k:v for k, v in rj.items()}
    #for k, v in rj.items():
    #    setattr(user, k, v)

    #return user.__dict__


class User(_controller):
    def __init__(self, *args):
        super(User, self).__init__(*args)

    def _get_user(self, username, swt, ldap):
        """

        :param username: string
        :param swt: Boolen
        :param ldap: Boolen
        :return: dict
        """
        user = {"ldap": None, "swt": None}
        user["ldap"] = get_user_ldap(username, self._config) if ldap else None
        user["swt"] = get_user_swt(username) if swt else None
        if user["swt"]:
            user["swt"]["created"] = None  # remove datime object, since json can't serialize it (could use  default=json_util.default param to json.dumps)
            user["swt"]["modified"] = None
        return user

    def get_user(self, username, swt=True, ldap=True):
        return self._get_user(username,  swt, ldap)

    def upsert_user(self, username, data):
        if not int(data.get("user_has_been_updated")):
            return False
        conn = g._db
        db_name = self._config.get("MySql", "db")
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM Users WHERE `username` LIKE \"{}\"".format(username))
            res = cursor.fetchall()
            if not res:
                query = """INSERT INTO `{}`.`Users` (`username`, `name`, `institution`, `street_address`, `city`, `state_province`, `zipcode`, `country`, `daytime_phone`, `email`, `created`, `modified` )
                  VALUES (\"{}\", \"{}\", \'{}\', "{}", \"{}\", \"{}\", \"{}\", \"{}\", \"{}\", NOW(), NOW())"""\
                    .format(db_name,
                            data.get("username", ""),
                            data.get("name", ""),
                            data.get("institution", ""),
                            data.get("street_address", ""),
                            data.get("zipcode", ""),
                            data.get("city", ""),
                            data.get("state_province", ""),
                            data.get("country", ""),
                            data.get("daytime_phone", ""),
                            data.get("email", ""))
                try:
                    res = cursor.execute(query)
                    if res:
                        conn.commit()
                except Exception as e:
                    self._logger.error("Failed to insert user information", exc_info=True)
                    raise ApiSqlException(description="Failed to insert user information")
            else:
                query = """UPDATE `{}`.`Users` SET
                                  `name`=\"{}\",
                                  `institution`=\"{}\",
                                   `street_address`=\"{}\",
                                   `city`=\"{}\",
                                    `state_province`=\"{}\",
                                    `zipcode`=\"{}\",
                                    `country`=\"{}\",
                                     `daytime_phone`=\"{}\",
                                     `email`=\"{}\",
                                    `modified`=NOW()
                                  WHERE `username` LIKE \"{}\"""" \
                    .format(db_name,
                            data.get("name", ""),
                            data.get("institution", ""),
                            data.get("street_address", ""),
                            data.get("city", ""),
                            data.get("state_province", ""),
                            data.get("zipcode", ""),
                            data.get("country", ""),
                            data.get("daytime_phone", ""),
                            data.get("email", ""),
                            data.get("username", ""),
                            )
                try:
                    res = cursor.execute(query)
                    if res:
                        conn.commit()
                except Exception as e:
                    self._logger.error("Failed to update user information", exc_info=True)
                    raise ApiSqlException(description="Failed to update user information")
        return True


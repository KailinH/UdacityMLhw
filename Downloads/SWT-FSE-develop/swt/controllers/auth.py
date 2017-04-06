from ._controller import ModelControllerFactory as _controller
from swt.schema.models.user import UserLdap, UserSwt, User
import jwt
import time

class Auth(_controller):
    def __init__(self, *args):
        super(Auth, self).__init__(*args)

    def get_token(self, user):
        username = user.get("ldap", {}).get("actor_username")
        first_last_name = "{} {}".format(user.get("ldap", {}).get("actor_first_name", username),
                                         user.get("ldap", {}).get("actor_last_name", username))
        #roles = user.get("ldap", {}).get("groups")
        try:
            digs = list(map(lambda x: x.split("-CoreAdmin")[0], filter(lambda x: "coreadmin" in x.lower(), user.get("ldap", {}).get("groups").keys())))
        except:
            """actor api group is a empty list when there's no values (otherwise it's an object of objects)
            """
            digs = []

        if user:
            payload = dict()
            payload["Audience"] = self._config.get("api", "origin")
            payload["Id"] = "57420e258cc15"
            payload["IssuedAt"] = time.time()
            payload["IssuedAt"] = time.time()
            payload["Expiration"] = time.time() + 43200
            payload["username"] = username
            payload["first_last_name"] = first_last_name
            #payload["roles"] = roles
            payload["digs"] = digs

            encoded = jwt.encode(payload, self._config.get("jwt", "secret"), algorithm='HS256')

            return encoded.decode("utf-8")

            #decoded = jwt.decode(encoded, self._config.get("jwt", "secret"), algorithms=['HS256'])

    """
    @get_user.setter
    def get_user(self, **kwargs):
        _user = UserSwt()
        for k, v in kwargs.items():
            if k in list(filter(lambda x: not x.startswith("__"), dir(UserSwt))):
                setattr(_user, k, v)
    """

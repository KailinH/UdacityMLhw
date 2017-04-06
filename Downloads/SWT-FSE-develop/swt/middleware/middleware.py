from flask import request, make_response
from bson import json_util
import json
from flask import g
from swt.controllers.user import get_user_ldap, get_user_swt
import jwt
import re
import pymysql as db
from swt.exceptions.api_expections import ApiSqlException


AUTHORIZED_PATHS = ["/authorizationtoken"]


def authenticate(token, secret):
    try:
        jwt.decode(token, secret, algorithms=['HS256'])
    except:
        return False
    else:
        return True


def get_user(username, _config):
    user = dict()
    user["ldap"] = get_user_ldap(username, _config)
    user["swt"] = get_user_swt(username)
    return user


def prepare_request(config):
    no_token = False
    p = re.compile("|".join(AUTHORIZED_PATHS))
    if p.match(request.path):
        no_token = True
    if not no_token:
        headers = request.headers
        try:
            try:
                token = headers["Authorization"]
            except:
                token = headers["Authtoken"]
            token = token.split()[-1]  # remove 'Bearer'
            token_payload = authenticate(token, config.get("jwt", "secret"))
            if not token_payload:
                return json.dumps({}), 401

        except Exception as e:
            #print(e)
            return json.dumps({"error": "error validating token"}), 412
        else:
            g._db = db.connect(host=config.get("MySql", "host"),
                              user=config.get("MySql", "user"),
                              passwd=config.get("MySql", "passwd"),
                              port=int(config.get("MySql", "port")),
                              db=config.get("MySql", "db"))

            decoded_token = jwt.decode(token, config.get("jwt", "secret"), algorithms=['HS256'])
            g.username = decoded_token.get("username")
            request.user = get_user(decoded_token.get("username"), config)
            try:
                user_digs = list(map(lambda x: x.split("-CoreAdmin")[0], filter(lambda x: "coreadmin" in x.lower(), request.user.get("ldap", {}).get("groups").keys())))
            except:
                user_digs = []
            with g._db.cursor() as cursor:
                query = """
                SELECT digs_core_number, digs_core_name FROM {}.Digs;
                """.format(config.get("MySql", "db"))
                try:
                    cursor.execute(query)
                except Exception:
                    raise ApiSqlException()
                else:
                    columns = [field[0] for field in cursor.description]
                    res = []
                    for row in cursor:
                        res.append({k: v for k, v in zip(columns, row)})

                    digs = {x["digs_core_name"]: x["digs_core_number"] for x in res}

                user_digs_dict = {v:k for k, v in digs.items() if k in user_digs}
                request.user["digs"] = user_digs_dict

    else:
        g._db = db.connect(host=config.get("MySql", "host"),
                           user=config.get("MySql", "user"),
                           passwd=config.get("MySql", "passwd"),
                           port=int(config.get("MySql", "port")),
                           db=config.get("MySql", "db"))


def prepare_response(response):

    try:
        status_c = int(response.status)
    except Exception:
        status_c = int(response.status_code)
    try:
        g._db.close()
    except:
        pass  # no db connection to close
    try:
        r = make_response(json.dumps(json.loads(response.data.decode("utf-8").strip()), default=json_util.default), status_c)
    except json.decoder.JSONDecodeError:
        r = make_response(json.dumps(str(response.data.decode("utf-8").strip()), default=json_util.default), status_c)

    r.headers['Access-Control-Allow-Origin'] = "*"
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    r.headers[
        'Access-Control-Allow-Headers'] = "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"
    r.headers["Content-type"] = "application/json; charset=utf-8"
    r.headers["Access-Control-Allow-Credentials"] = 'true'
    r.headers["Accept"] = "*/*"
    return r

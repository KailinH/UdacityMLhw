from flask_restful import Resource, request
from werkzeug.urls import url_decode
from swt.exceptions.api_expections import ApiPreconditionFailedException

class UserUsername(Resource):
    def post(self):
        pass

    def get(self, username):
        user = self.controllers.user.get_user(username, ldap=False)
        if not user:
            return user, 412
        return {"status": True, "user": user}, 200

    def put(self, username):
        try:
            data = {k: v[0] for k, v in dict(url_decode(request.get_data())).items()}
        except Exception as e:
            self._logger.error("can't read put data", exc_info=True)
            raise ApiPreconditionFailedException(description="Application Error.")
        else:
            res = self.controllers.user.upsert_user(username, data)
        return {"result": res}

    def patch(self):
        pass
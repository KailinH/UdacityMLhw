from flask_restful import Resource, request
import json
from werkzeug.urls import url_decode

class Extracts(Resource):

    def get(self):
        extracts = self.controllers.extracts.get_extracts(request.user)
        return extracts, 200

    def post(self):
        payload = request.get_json(force=True)
        insertion = self.controllers.extracts.insert_extracts(request.user, payload)
        return insertion, 201

    def put(self):
        try:
            payload = dict(url_decode(request.get_data()))
        except Exception:
            try:
                payload = request.get_json(force=True)
            except Exception:
                try:
                    payload = json.loads(request.data.decode("utf-8"))
                except Exception:
                    return {"status": False}, 500
        update = self.controllers.extracts.update_status(request.user, payload=payload)

        if update:
            return {"status":True}, 200
        return {"status":False}, 500


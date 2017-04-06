from flask import request
from flask_restful import Resource


class Facilities(Resource):
    def post(self):
        try:
            data = request.get_json(force=True)
            zipcode = data.get('zipcode', None)
        except Exception as e:
            print(e)
        number_extracts = int(data.get("number_extracts", None))
        sequencing_tech = data.get("sequencing_tech", None)
        #analysis_type = data.get("analysis_type", None)
        response = None
        try:
            facilities = self.controllers.fse.select_facility(zipcode, number_extracts, sequencing_tech)
        except Exception as e:
            response = {
                    'result': e.description if hasattr(e, "description") else None,
                    'description': e.description if hasattr(e, "description") else None,
                    'error_code': e.code if hasattr(e, "code") else None
                }
        else:
            response = {
                    'result': facilities,
                    'error_code': 0
                }
        finally:
            return response, 200


class FacilitiesValidate(Resource):
    def head(self, zipcode):
        """Validate the zipcode.
        Call to validate_zipcode will throw a precondition failed exception if it fails
        :param zipcode:
        :return:
        """
        self.controllers.fse.validate_zipcode(zipcode)
        return None, 200
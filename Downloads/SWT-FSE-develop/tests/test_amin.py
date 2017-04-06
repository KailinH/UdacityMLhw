import sys, os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path + "/..")
import unittest
import pytest
from swt.swt_app import create_app as create_app_
from flask.ext.testing import TestCase
from urllib.request import urlopen
from flask_testing import LiveServerTestCase
from flask import request
from flask import appcontext_pushed, g
from flask import Response
from swt.controllers.fse import FSE
from swt.exceptions.api_expections import ApiPreconditionFailedException
import json

class TestFse(unittest.TestCase):

    @pytest.fixture
    def create_app(self):
        app = create_app_()
        app.config['TESTING'] = True
        return app

    def test_zipcode_validation(self):

        assert FSE.validate_zipcode(11215, 10029)
        #assert FSE.validate_zipcode(11215, "10029a")

        #self.assertRaises(ApiPreconditionFailedException, FSE.validate_zipcode(11215, "10029a"))

    def test_endpoint_authorizationtoken(self):
        app = self.create_app()
        app_ = app.test_client()
        res = app_.get("/authorizationtoken/lcunha")
        data = res.data
        data = data.decode("utf-8")
        status_code = res.status_code
        assert status_code == 200
        assert len(data) > 50
        assert "." in data

    def test_endpoint_extracts(self):
        app = self.create_app()
        app_ = app.test_client()
        data = app_.get("/authorizationtoken/lcunha").data
        token = data.decode("utf-8")[1:-1]
        auth_header = """{} {}""".format("Bearer", token)
        resp = app_.get("/extracts/", headers = {'Authorization': auth_header})
        assert resp.status_code == 200
        res = json.loads(resp.data.decode("utf-8"))
        assert "status" in res
        assert res.get("status") == True
        assert "core" in res
        assert len(res.get("requesters", {})) > 0
        assert len(res.get("extracts", [])) > 0

    def test_app(self):
        app = self.create_app()
        app_ = app.test_client()
        with app.test_request_context('/authorizationtoken/lcunha', method='get'):
            print("0", getattr(g, '_db', None))  # g not available yet. need to pre-process request
            # now you can do something with the request until the
            # end of the with block, such as basic assertions:
            #assert request.path == '/extracts/'
            #assert request.method == 'GET'
            print("A", app.preprocess_request())
            print(getattr(g, '_db', None))  # g is only available after pre-processing the request (and within this request context)
            resp = Response("a")
            print("B", app.process_response(resp))
        #sys.stderr.write("world\n")
        assert True
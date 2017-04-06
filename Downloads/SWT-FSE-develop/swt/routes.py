from .resources.fse import Facilities, FacilitiesValidate
from .resources.extracts import Extracts, ExtractsId
from .resources.users.user_by_username import UserUsername
from .resources.auth.auth import AuthorizationToken


routes = {
    "/fse/": Facilities,
    "/fse/<zipcode>": FacilitiesValidate,
    "/extracts/": Extracts,
    "/extracts/<id>": ExtractsId,
    "/users/<username>": UserUsername,
    "/authorizationtoken/<username>": AuthorizationToken

}
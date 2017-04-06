"""
class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv
"""

import os
import falcon
import configparser


class ApiException(Exception):
    """
    Generic class to handle APIExceptions
    Note: We should not be throwing this Exception unless there is an no relevant subclass present
    this by default sets the status code to 500
    we support the message code to support legacy APIException class which reads from the ini file to set the
    error description.
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_500, exception_code=None, language='us_en',
                 **kwargs):
        """
        :param title: optional string. default to "Internal Server Error".
        :param description: optional string . default: "There was an error in your request". This can also
               be overridden by passing a message code which looks for the description in the exceptions.ini file
        :param code: http_status_code.
        :param exception_code: code if present in the exceptions.ini file
        :param kwargs: any additional params to be sent in the body of the response
        :return: None
        """
        self.title = title if title else 'Internal Server Error'
        self.description = self.get_exception_message(exception_code, language) if exception_code \
            else description if description else 'Looks like something went wrong. Please try again later.'

        self.additional_params = kwargs
        self.code = code

    @staticmethod
    def handle(ex, req, resp, params):

        resp.status = ex.code
        resp.body = {
            'title': ex.title,
            'description': ex.description,
            'additional_info': ex.additional_params,
            "status": False,
            "statusText": ex.description
        }

    @staticmethod
    def get_exception_message(exception_key, language):
        """
        Extracts the exception message for a given exception key from the config exceptions file
        :param exception_key: key to find in config exceptions file
        :param language: string
        :rtype exception_description: string
        """
        config = configparser.ConfigParser()
        exceptions_list_path = os.path.dirname(os.path.realpath(__file__)) + '/api_exceptions_' + language + '.ini'
        config.read_file(open(exceptions_list_path))

        return config.get("EXCEPTIONS", exception_key)


class ApiInvalidPayloadException(ApiException):
    """
    JSON schema validator exception. This exception adds json schema message and path to the exception
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_412, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Invalid Payload'
        description = description if description else 'Request payload is invalid.'

        super(ApiInvalidPayloadException, self).__init__(title=title, description=description, code=code,
                                                         exception_code=exception_code, **kwargs)



class ApiJsonSchemaValidationException(ApiException):
    """
    JSON schema validator exception. This exception adds json schema message and path to the exception
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_422, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Json Schema Error'
        description = description if description else 'The payload verification failed.'

        if 'json_schema_path' in kwargs:
            kwargs['json_schema_path'] = '-'.join(str(item) for item in kwargs['json_schema_path'])

        super(ApiJsonSchemaValidationException, self).__init__(title=title, description=description, code=code,
                                                               exception_code=exception_code, **kwargs)


class ApiNoResultSet(ApiException):
    """
    an "exception" (though not really. read below) to be thrown when attempting to build a result set that results in
     an empty response.

    NOTE: this does NOT return a status code indicating a problem. It returns a 204. This should be used when a result
          set can be optionally empty and not indicate problems for the requester (i.e., requesting a list of resources
          that may or may not actually exist.)
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_412, exception_code=None, **kwargs):
        """
        title and description do not have default values as responses without content do not always require an
         explanation.
        """
        super(ApiNoResultSet, self).__init__(title=title, description=description, code=code,
                                             exception_code=exception_code, **kwargs)


class ApiPreconditionFailedException(ApiException):
    """
    precondition failed exception
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_412, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Precondition failed'
        description = description if description else 'a pre-condition for the request payload failed.'

        super(ApiPreconditionFailedException, self).__init__(title=title, description=description, code=code,
                                                             exception_code=exception_code, **kwargs)


class ApiPresentationException(ApiException):
    """
    This exception should be raised when an error during presentation modifications occurs.
    """

    def __init__(self, title=None, description=None, code=falcon.HTTP_500, exception_code=None, **kwargs):
        title = title if title else 'Presentation failure'
        description = description if description else 'An error occurred when attempting to modify the presentation ' \
                                                      'of the requested resource.'

        super(ApiPresentationException, self).__init__(title=title, description=description, code=code,
                                                       exception_code=exception_code, **kwargs)


class ApiResourceAlreadyExists(ApiException):
    """
    This exception should be raised when a request to create a resource that already exists is made.

    NOTE: this is only necessary to raise when there is a need to preserve unique aspects of resources AND inform
          the user that a resource already exists.
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_409, exception_code=None, **kwargs):
        title = title if title else 'Resources already exists'
        description = description if description else 'The resource attempting to be created already exists.'

        super(ApiResourceAlreadyExists, self).__init__(title=title, description=description, code=code,
                                                       exception_code=exception_code, **kwargs)


class ApiResourceNotFoundException(ApiException):
    """ Resource not found exception. """
    def __init__(self, title=None, description=None, code=falcon.HTTP_404, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Resource Not Found Error'
        description = description if description else 'The requested resource could not be found.'

        super(ApiResourceNotFoundException, self).__init__(title=title, description=description, code=code,
                                                           exception_code=exception_code, **kwargs)


class ApiRethinkException(ApiException):
    """
    rethink db exception, will throw a 500 status unless overridden
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_500, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Rethink Error'
        description = description if description else 'There was a rethink db operation error.'

        super(ApiRethinkException, self).__init__(title=title, description=description, code=code,
                                                  exception_code=exception_code, **kwargs)


class ApiSqlException(ApiException):
    """
    Generic SqlAlchemyException. Will throw a 500 status unless overridden
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_412, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'MySQL Error'
        description = description if description else 'A postgres operation failed.'

        super(ApiSqlException, self).__init__(title=title, description=description, code=code,
                                              exception_code=exception_code, **kwargs)


class ApiSqlIntegrityException(ApiSqlException):
    """
    sqlalchemy integrity exception, will throw a 400 status unless overridden
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_400, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Postgres Integrity Error'
        description = description if description else 'There was a postgres integrity error.'

        super(ApiSqlException, self).__init__(title=title, description=description, code=code,
                                              exception_code=exception_code, **kwargs)


class ApiUserNotAuthenticatedException(ApiException):
    """
    This exception should be raised when any type of request does not contain a valid token value. Will only be used
    by the auth middleware
    """

    def __init__(self, title=None, description=None, code=falcon.HTTP_403, exception_code=None, **kwargs):
        title = title if title else 'Access denied.'
        description = description if description else 'Please provide a valid authentication token.'
        super(ApiUserNotAuthenticatedException, self).__init__(title=title, description=description, code=code,
                                                               exception_code=exception_code, **kwargs)


class ApiUserNotAuthorizedException(ApiException):
    class ApiNoResultSet(ApiException):
        """
        This exception should be raised when any type of request is made against a resource that the requester is not
         authorized to view and/or change.
        """

    def __init__(self, title=None, description=None, code=falcon.HTTP_403, exception_code=None, **kwargs):
        title = title if title else 'Access denied.'
        description = description if description else 'You are not authorized to view the requested resource.'
        super(ApiUserNotAuthorizedException, self).__init__(title=title, description=description, code=code,
                                                            exception_code=exception_code, **kwargs)

class ApiUnauthorizedOperationException(ApiException):
    """
    Generic SqlAlchemyException. Will throw a 500 status unless overridden
    """
    def __init__(self, title=None, description=None, code=falcon.HTTP_500, exception_code=None, **kwargs):
        """
        :rtype: None
        """
        title = title if title else 'Api Error'
        description = description if description else 'Operation not authorized.'

        super(ApiUnauthorizedOperationException, self).__init__(title=title, description=description, code=code,
                                              exception_code=exception_code, **kwargs)
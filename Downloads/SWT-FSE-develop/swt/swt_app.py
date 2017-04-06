from .middleware.middleware import prepare_response, prepare_request
from .controllers._controller import ModelControllerFactory
import configparser
from flask import Flask
from flask_restful import Api
import logging.handlers
from logging.config import dictConfig
import os
import datetime

from gevent import monkey
monkey.patch_socket()
import gevent
from gevent.queue import Queue
from functools import partial
from swt.routes import routes
from logger_config import LOG_CONFIG

# TODO: automated deployment should create the log dir
try:
    os.makedirs('/var/log/swt/fse/')
except:
    pass #dir exists
#LOG_FILENAME = '/var/log/swt/fse/' + __name__ + "_" + str(time.time()) + '.log'

LOG_FILENAME = '/var/log/swt/fse/' + __name__ + "_" + str(datetime.date.today()) + '.log'



_log_config = LOG_CONFIG
_log_config["handlers"]["file"]["filename"] = LOG_FILENAME
_log_config['loggers']["fse"]["level"] = "INFO"
dictConfig(_log_config)
_logger = logging.getLogger('fse')
LOGGER = _logger


class ConnectionPool:
    def __init__(self, db_config, time_to_sleep=5, max_pool_size = 10, test_run=False):
        self.username = db_config.get('user')
        self.password = db_config.get('password')
        self.host = db_config.get('host')
        self.port = int(db_config.get('port'))
        self.db = db_config.get('db')
        self.max_pool_size = max_pool_size
        self.test_run = test_run
        self.pool = None
        self.time_to_sleep = time_to_sleep
        self._initialize_pool()
        self._re_initialize_pool()

    def get_initialized_connection_pool(self):
        return self.pool

    def _initialize_pool(self):
        self.pool = Queue(maxsize=self.max_pool_size)
        current_pool_size = self.pool.qsize()
        if current_pool_size < self.max_pool_size:  # this is a redundant check, can be removed
            for _ in range(0, self.max_pool_size - current_pool_size):
                try:
                    conn = db.connect(host=self.host,
                                      user=self.username,
                                      passwd=self.password,
                                      port=self.port,
                                      db=self.db)
                    self.pool.put_nowait(conn)

                except db.OperationalError as e:
                    LOGGER.error("Cannot initialize connection pool - retrying in {} seconds".format(self.time_to_sleep))
                    LOGGER.exception(e)
                    break
        self._check_for_connection_loss()

    def _re_initialize_pool(self):
        gevent.sleep(self.time_to_sleep)
        self._initialize_pool()

    def _check_for_connection_loss(self):
        while True:
            conn = None
            if self.pool.qsize() > 0:
                conn = self.pool.get()

            if not self._ping(conn):
                if self.test_run:
                    self.port = 3306

                self._re_initialize_pool()

            else:
                self.pool.put_nowait(conn)

            if self.test_run:
                break
            gevent.sleep(self.time_to_sleep)

    def _ping(self, conn):
        try:
            if conn is None:
                conn = db.connect(host=self.host,
                                  user=self.username,
                                  passwd=self.password,
                                  port=self.port)
            cursor = conn.cursor()
            cursor.execute('select 1;')
            LOGGER.debug(cursor.fetchall())
            return True

        except db.OperationalError as e:
            LOGGER.warn('Cannot connect to mysql - retrying in {} seconds'.format(self.time_to_sleep))
            LOGGER.exception(e)
            return False


config = configparser.ConfigParser()
config_path = os.path.dirname(os.path.realpath(__file__)) + '/config.ini'
config.read_file(open(config_path))
HOST = config.get('MySql', 'host')
PORT = int(config.get('MySql', 'port'))
DB = config.get('MySql', 'db')
USER = config.get('MySql', 'user') #os.getenv("RDS_SWT_USERNAME", "sl_dev_app")
PASSWD = config.get('MySql', 'passwd') #os.getenv("RDS_SWT_PASSWD", "sl_dev_@pp20878!")

"""
config_db = {
    'user': USER,
    'password': PASSWD,
    'host': HOST,
    'port': PORT,
    'db': "DPCC_SWT_DEV"
}

conn_pool = ConnectionPool(config_db, time_to_sleep=5, max_pool_size=3, test_run=True)
pool = conn_pool
"""

# custom error messages to be included on the body of error response
errors = {
    'UserAlreadyExistsError': {
        'message': "A user with that username already exists.",
        'status': 409,
    },
    'ResourceDoesNotExist': {
        'message': "A resource with that ID no longer exists.",
        'status': 410,
        'extra': "Any extra information you want.",
    },
    "ApiException":   {
        'message': "A Application error happened.",
        'status': 500,
        'extra': "Any extra information you want.",
    },
}


def create_app():
    app = Flask(__name__)
    api = Api(app, errors=errors)

    for uri, resource in routes.items():
        resource.logger = _logger
        resource.controllers = ModelControllerFactory(resource, config, _logger)
        resource.config = config
        api.add_resource(resource, uri)


    pre_process = partial(prepare_request, config)

    # Middleware hooks
    app.before_request(pre_process)
    #print(app.get)
    app.after_request(prepare_response)
    return app


#def log_exception(sender, exception, **extra):
#    """ Log an exception to our logging framework """
#    sender.logger.debug('Got exception during processing: %s', exception)
#
#from flask import got_request_exception
#got_request_exception.connect(log_exception, app)


if __name__ == '__main__':
    #app.run(port=5003)
    config_db = {
        'user': USER,
        'password': PASSWD,
        'host': HOST,
        'port': PORT
    }
    conn_pool = ConnectionPool(config_db, time_to_sleep=5, max_pool_size=3, test_run=True)
    pool = conn_pool.get_initialized_connection_pool()
    # when in test run the port will be switched back to 3306
    # so the queue size should be 20 - will be nice to work
    # around this rather than test_run hack
    assert pool.qsize() == 3
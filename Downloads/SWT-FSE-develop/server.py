#from tornado.wsgi import WSGIContainer
#from tornado.httpserver import HTTPServer
#from tornado.ioloop import IOLoop
from swt.swt_app import create_app
#from wsgiref import simple_server
from gevent.wsgi import WSGIServer


app = create_app()

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()


#httpd = simple_server.make_server('0.0.0.0', 5002, api)
#httpd.serve_forever()


#http_server = HTTPServer(WSGIContainer(app))
#http_server.listen(5002)
#IOLoop.instance().start()

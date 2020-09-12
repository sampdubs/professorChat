from webapp import app as application
from eventlet import wsgi, listen

if __name__ == "__main__":
    print("Starting server...")
    wsgi.server(listen(('', 80)), application)
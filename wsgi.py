import eventlet
eventlet.monkey_patch()
from app import create_app
from eventlet import wsgi

app = create_app()
wsgi.server(eventlet.listen(("0.0.0.0", 5000)), app)

if __name__ == "__main__":
    #socketio.run(app=app)
    wsgi.server(eventlet.listen(("0.0.0.0", 5000)), app)
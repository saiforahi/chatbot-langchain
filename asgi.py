from asgiref.wsgi import WsgiToAsgi
from app import create_app

asgi_app = WsgiToAsgi(create_app())

# import asyncio
# from hypercorn.config import Config
# from hypercorn.asyncio import serve
#
# asyncio.run(serve(create_app(), Config().from_pyfile("hypercorn_config.py")))


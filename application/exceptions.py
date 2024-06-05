# application/exceptions.py

from application.controllers.baseController import BaseController


# application/exceptions.py


class UnauthorizedException(Exception):
    def __init__(
        self, message="You are not authorized to perform this action", status_code=401
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.controller = BaseController()

    def to_error_response(self):
        return self.controller.error_response(
            message=self.message, status_code=self.status_code
        )

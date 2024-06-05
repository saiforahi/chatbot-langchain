from flask import jsonify, url_for, request


class BaseController:
    def __init__(self) -> None:
        pass

    def success_response(self, message="", data=None, status_code=200,  pagination=None, extra=None):
        success_payload = {
            "success": True,
            "message": message,
            "data": data,
            "extra": extra 
        }
        if pagination:
            success_payload["pagination"] = pagination
        return jsonify(success_payload), status_code

    def error_response(self, message="", errors=[], status_code=400, extra=None):
        error_payload = {
            "success": False,
            "message": message,
            "errors": {'json':errors},
            "extra": extra 
        }
        return jsonify(error_payload), status_code
    
    def get_pagination_dict(self, items):
        pagination = {
            "total": items.total,
            "per_page": items.per_page,
            "current_page": items.page,
            "last_page": items.pages,
            "next_page_url": url_for(request.endpoint, page=items.next_num) if items.has_next else None,
            "prev_page_url": url_for(request.endpoint, page=items.prev_num) if items.has_prev else None,
            "from": items.prev_num,
            "to": items.next_num

            
        }
        return pagination

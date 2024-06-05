from flask import current_app, jsonify, Response
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from application.models.memberShipModels import UserMembership
from application.models.chatbotModel import Chatbot
from flask import request
import os
from constants import APPLICATION_JAVASCRIPT, WIDGET_TOKEN_PARAM

js_blueprint = Blueprint(
    "js", __name__, description="JavaScript Serving", url_prefix="/api"
)
stage = os.getenv("APP_ENV", "local")
base_url = {
    "dev": "https://dev.shadhin.ai",
    "stage": "https://app.shadhin.ai",
    "local": "localhost:5000",
}
base_url = base_url.get(stage)


@js_blueprint.route("/chatImplementHandler/<string:chatbot_id>")
class ChatImplementHandler(MethodView):
    def get(self, chatbot_id):
        try:
            widget_token = request.args.get(WIDGET_TOKEN_PARAM)
            if not widget_token:
                return jsonify({"error": "You have no membership"}), 400

            chatbot: Chatbot = Chatbot.query.filter_by(id=chatbot_id).first()

            if not chatbot:
                return jsonify({"error": "Chatbot not found"}), 404

            if not self._is_access_granted(chatbot, widget_token):
                return jsonify({"error": "You don't have access to this chatbot"}), 403

            iframe_src = f"{base_url}/embedded-chat/{chatbot_id}/{widget_token}"
            script_content = self._generate_script_content(iframe_src)
            return Response(script_content, mimetype=APPLICATION_JAVASCRIPT)

        except Exception as error:
            current_app.logger.error(f"Error generating script: {error}")
            return jsonify({"error": "Internal Server Error"}), 500

    def _is_access_granted(self, chatbot, widget_token):
        return (
            chatbot.widget_token == widget_token
            and UserMembership.query.filter_by(
                user_id=chatbot.created_by, is_active=True
            ).first()
        )

    def _generate_script_content(self, iframe_src):
        script_content = f"""
            document.addEventListener('DOMContentLoaded', () => {{
                const iframe = document.createElement('iframe');
                iframe.id = 'myCustomIframe';
                iframe.src = "{iframe_src}";
                const style = document.createElement('style');

                style.textContent = `
                    #myCustomIframe {{
                        width: 400px; 
                        height: 600px;
                        z-index: 9999;
                        position: fixed; 
                        bottom: 4vh; 
                        right: 4%; 
                        border: 0;
                    }}

                    @media only screen and (max-width: 600px) {{
                        #myCustomIframe {{
                            bottom: 0;
                            right: 0;
                            width: 100%;
                            height: 100%;
                        }}
                    }}
                `;
                document.head.appendChild(style);

                document.body.appendChild(iframe);
            }});
            """
        return script_content

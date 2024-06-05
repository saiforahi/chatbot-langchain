from application.controllers.baseController import BaseController
from application.models.system_settings_model import SystemSetting
from application.schemas.common_schema import SystemSettingSchema


class UtilityController(BaseController):
    def __init__(self):
        super().__init__()

    def get_system_settings(self):
        try:
            settings=SystemSetting.query.all()
            if len(settings)>0:
                settings=SystemSettingSchema(many=False).dump(settings[0])
            else: settings=None

            return self.success_response(message="System Settings",data=settings,status_code=200)
        except Exception as e:
            return self.error_response(message=str(e),status_code=500)
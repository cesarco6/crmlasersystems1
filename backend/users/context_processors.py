import json
import os
from django.conf import settings

def global_settings_processor(request):
    font = 'ubuntu'
    settings_file = os.path.join(settings.BASE_DIR, 'global_settings.json')
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                data = json.load(f)
                font = data.get('crm_font', 'ubuntu')
        except Exception:
            pass
    return {'GLOBAL_CRM_FONT': font}

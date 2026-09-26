from django.conf import settings


def cometchat_settings(request):
    return {
        "COMETCHAT_APP_ID": getattr(settings, "COMETCHAT_APP_ID", ""),
        "COMETCHAT_REGION": getattr(settings, "COMETCHAT_REGION", ""),
    }

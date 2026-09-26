from django.shortcuts import redirect
from django.views.i18n import set_language as django_set_language


def set_language(request):
    response = django_set_language(request)
    language = request.POST.get("language")
    if language in {"en", "gu", "hi"} and request.user.is_authenticated:
        request.user.profile.preferred_language = language
        request.user.profile.save(update_fields=("preferred_language", "updated_at"))
    return response

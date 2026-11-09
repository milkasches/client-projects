from django.conf import settings


def site(request):
    return {
        "contact_email": settings.CONTACT_EMAIL,
        "facebook_url": settings.FACEBOOK_URL,
    }

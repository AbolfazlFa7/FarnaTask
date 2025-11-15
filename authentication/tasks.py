from celery import shared_task
from django.core.mail import EmailMultiAlternatives


@shared_task(bind=True)
def send_email(self, subject, body, from_email, to):
    email = EmailMultiAlternatives(subject, body, from_email, to)

    email.content_subtype = 'html'

    res = email.send()
    if self.request.retries < 3:
        if not res:
            self.retry(countdown=5)
    return f'{subject} - {to}'


@shared_task(bind=True)
def send_phone(self, api, params):
    res = api.send_sms(params)

    if self.request.retries < 3:
        if not res:
            self.retry(countdown=5)
    return f'{params["receptor"]}'

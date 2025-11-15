from django.conf import settings
import requests


def request_payment(amount, description, order_id, currency="IRR"):
    base_url = f'https://{"sandbox" if settings.ZARINPAL_SANDBOX else "payment"}.zarinpal.com/'
    request_url = base_url + 'pg/rest/WebGate/Initiate.json'

    data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': amount,
        'currency': currency,  # or 'IRT   | not required, by default IRR
        'description': description,
        'callback_url': settings.ZARINPAL_CALLBACK_URL,
        'metadata': {'order_id': order_id},
    }
    response = requests.post(request_url, json=data)
    if response.status_code == 200:
        data = response.json()['data']
        if data['code'] == 100:
            authority = data['data']['authority']
            payment_url = base_url + f"pg/StartPay/{authority}"
            return authority, payment_url
    return None, None


def verify_payment(authority, amount):
    base_url = f'https://{"sandbox" if settings.ZARINPAL_SANDBOX else "payment"}.zarinpal.com/'
    verify_url = base_url + 'pg/rest/WebGate/Verify.json'

    data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'authority': authority,
        'amount': amount
    }
    response = requests.post(verify_url, json=data)
    if response.status_code == 200:
        data = response.json()['data']
        if data['code'] == 100 or data['code'] == 101:
            return data['ref_id'], 'success'
        else:
            return None, 'failed'
    return None, 'error'

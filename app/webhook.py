import requests
import json
from app.models import Webhook

def send_webhook(event, data):
    """Kirim notifikasi ke semua webhook yang cocok."""
    webhooks = Webhook.query.filter_by(is_active=True).all()
    for webhook in webhooks:
        if webhook.event == 'all' or webhook.event == event:
            try:
                payload = {
                    'event': event,
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                response = requests.post(
                    webhook.url,
                    json=payload,
                    timeout=5,
                    headers={'Content-Type': 'application/json'}
                )
                print(f'Webhook {webhook.name}: {response.status_code}')
            except Exception as e:
                print(f'Webhook {webhook.name} error: {e}')
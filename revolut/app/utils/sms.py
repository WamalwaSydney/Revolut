import africastalking
from flask import current_app

def initialize_sms():
    """Initialize Africa's Talking SMS service"""
    africastalking.initialize(
        username=current_app.config['AFRICASTALKING_USERNAME'],
        api_key=current_app.config['AFRICASTALKING_API_KEY']
    )
    return africastalking.SMS()

def send_sms(phone_number, message):
    """Send SMS via Africa's Talking"""
    if not phone_number.startswith('+'):
        phone_number = f"+{phone_number}"

    sms = initialize_sms()
    try:
        response = sms.send(message, [phone_number])
        current_app.logger.info(f"SMS sent to {phone_number}: {response}")
        return True
    except Exception as e:
        current_app.logger.error(f"SMS failed to {phone_number}: {str(e)}")
        return False

def send_ussd_response(phone_number, message):
    """Send USSD prompt response"""
    sms = initialize_sms()
    try:
        response = sms.send(message, [phone_number], {
            'enqueue': True,
            'keyword': 'RevolutWDO'
        })
        return response
    except Exception as e:
        current_app.logger.error(f"USSD response failed: {str(e)}")
        return None
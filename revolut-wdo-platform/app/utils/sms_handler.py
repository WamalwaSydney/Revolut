import re
import africastalking
from flask import current_app

class SMSHandler:
    def __init__(self):
        self.ussd_session = {}
        self.sms = None  # Lazy initialization

    def _init_sms_service(self):
        """Initialize Africa's Talking SMS service within application context."""
        if self.sms is None:
            username = current_app.config.get('AFRICASTALKING_USERNAME')
            api_key = current_app.config.get('AFRICASTALKING_API_KEY')
            africastalking.initialize(username, api_key)
            self.sms = africastalking.SMS

    def send_sms(self, phone_number, message):
        """Send SMS using Africa's Talking API."""
        try:
            self._init_sms_service()
            response = self.sms.send(message, [phone_number])
            return response
        except Exception as e:
            current_app.logger.error(f"Failed to send SMS: {str(e)}")
            return None

    def parse_feedback_sms(self, message):
        """Parse SMS feedback in format: FEEDBACK <category> <county> <message>"""
        pattern = r'^FEEDBACK\s+(\w+)\s+(\w+)\s+(.+)$'
        match = re.match(pattern, message, re.IGNORECASE)
        if match:
            return {
                'is_valid': True,
                'category': match.group(1).lower(),
                'county': match.group(2),
                'content': match.group(3)
            }
        return {'is_valid': False}

    def process_ussd_request(self, session_id, service_code, phone_number, text):
        """Process USSD requests and return appropriate response."""
        session = self.ussd_session.get(session_id, {})

        if text == '':
            response = "CON Welcome to Revolut & WDO\n"
            response += "1. Submit Feedback\n"
            response += "2. View Feedback Status\n"
            response += "3. Participate in Poll\n"
            response += "4. Help"
            session['step'] = 'main_menu'
            self.ussd_session[session_id] = session
            return response

        steps = text.split('*')
        current_step = steps[-1]

        if session.get('step') == 'main_menu':
            if current_step == '1':
                response = "CON Select Feedback Category:\n"
                response += "1. Education\n"
                response += "2. Health\n"
                response += "3. Infrastructure\n"
                response += "4. Security\n"
                response += "5. Water\n"
                response += "6. Other"
                session['step'] = 'feedback_category'
                self.ussd_session[session_id] = session
                return response
            elif current_step == '2':
                response = "CON Enter your feedback reference number:"
                session['step'] = 'feedback_status'
                self.ussd_session[session_id] = session
                return response
            elif current_step == '3':
                response = "CON Select a poll to participate in:\n"
                response += "1. Budget Priorities Poll\n"
                response += "2. Service Rating Poll"
                session['step'] = 'poll_selection'
                self.ussd_session[session_id] = session
                return response
            else:
                return "END Thank you for using Revolut & WDO"

        elif session.get('step') == 'feedback_category':
            category_map = {
                '1': 'education',
                '2': 'health',
                '3': 'infrastructure',
                '4': 'security',
                '5': 'water',
                '6': 'other'
            }
            category = category_map.get(current_step)
            if category:
                session['category'] = category
                response = "CON Please enter your county:"
                session['step'] = 'feedback_county'
                self.ussd_session[session_id] = session
                return response
            else:
                return "END Invalid selection. Please try again."

        elif session.get('step') == 'feedback_county':
            session['county'] = current_step
            response = "CON Please enter your feedback message:"
            session['step'] = 'feedback_message'
            self.ussd_session[session_id] = session
            return response

        elif session.get('step') == 'feedback_message':
            feedback_text = current_step
            # Here you'd save feedback_text, session['category'], and session['county'] to DB

            response = "END Thank you! Your feedback has been submitted. Reference: #12345"
            self.ussd_session.pop(session_id, None)
            return response

        return "END Service not available. Please try again later."

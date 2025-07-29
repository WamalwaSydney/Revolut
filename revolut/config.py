import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    NLTK_DATA_PATH = os.getenv('NLTK_DATA_PATH', os.path.expanduser('~/nltk_data'))
    AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME')
    AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY')
    SMS_SHORTCODE = os.getenv('SMS_SHORTCODE')
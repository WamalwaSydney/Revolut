from app import db
from app.models import UserFeedback
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk

nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()


def process_feedback(feedback_id):
    feedback = UserFeedback.query.get(feedback_id)
    if not feedback or not feedback.content:
        return

    text = feedback.content

    # Sentiment analysis
    sentiment = sia.polarity_scores(text)
    feedback.sentiment_score = sentiment['compound']

    # Tagging
    words = word_tokenize(text.lower())
    stop_words = set(stopwords.words('english'))
    filtered_words = [
        word for word in words if word.isalnum() and word not in stop_words
    ]

    tags = []
    if any(word in ['water', 'pipe', 'supply'] for word in filtered_words):
        tags.append('water_supply')
    if any(word in ['road', 'construction', 'pothole']
           for word in filtered_words):
        tags.append('infrastructure')
    if any(word in ['health', 'hospital', 'clinic']
           for word in filtered_words):
        tags.append('healthcare')

    feedback.tags = tags
    feedback.is_processed = True
    db.session.commit()

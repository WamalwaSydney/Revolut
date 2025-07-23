from textblob import TextBlob
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon')

class SentimentAnalyzer:
    @staticmethod
    def analyze_sentiment(text):
        # Using TextBlob
        blob = TextBlob(text)
        sentiment_score = blob.sentiment.polarity
        
        # Classify sentiment
        if sentiment_score > 0.2:
            sentiment_label = 'positive'
        elif sentiment_score < -0.2:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        # Using NLTK VADER for more nuanced analysis
        sia = SentimentIntensityAnalyzer()
        vader_scores = sia.polarity_scores(text)
        
        # Combine both approaches
        combined_score = (sentiment_score + vader_scores['compound']) / 2
        
        return combined_score, sentiment_label

class AnalyticsDashboard:
    @staticmethod
    def get_feedback_stats(days=30):
        # In a real implementation, this would query the database
        return {
            'total_feedback': 2540,
            'resolved_feedback': 1872,
            'pending_feedback': 668,
            'avg_response_time': '2.5 days',
            'top_category': 'Infrastructure',
            'top_county': 'Nairobi'
        }
    
    @staticmethod
    def get_trending_issues(days=7):
        # In a real implementation, this would analyze recent feedback
        return [
            {'topic': 'Road Repairs', 'count': 142, 'sentiment': 'negative'},
            {'topic': 'School Fees', 'count': 98, 'sentiment': 'negative'},
            {'topic': 'Water Supply', 'count': 76, 'sentiment': 'positive'},
            {'topic': 'Healthcare', 'count': 65, 'sentiment': 'negative'}
        ]
    
    @staticmethod
    def get_user_engagement_stats():
        return {
            'active_users': 12540,
            'new_users': 342,
            'feedback_per_user': 3.2,
            'top_constituency': 'Kasarani'
        }

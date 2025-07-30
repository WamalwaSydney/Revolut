# app/utils/enhanced_nlp_processor.py
from app import db
from app.models import UserFeedback
from textblob import TextBlob
import re
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class EnhancedNLPProcessor:
    def __init__(self):
        # Expanded keyword mappings for better categorization
        self.category_keywords = {
            'water_supply': [
                'water', 'pipe', 'supply', 'tap', 'borehole', 'well', 'dam', 'reservoir',
                'maji', 'bomba', 'kiosk', 'shortage', 'quality', 'clean', 'dirty',
                'sewer', 'sewage', 'drainage', 'flood'
            ],
            'infrastructure': [
                'road', 'construction', 'pothole', 'bridge', 'street', 'highway',
                'barabara', 'jengo', 'building', 'repair', 'maintenance', 'tarmac',
                'murram', 'pathway', 'sidewalk', 'lighting', 'streetlight'
            ],
            'healthcare': [
                'health', 'hospital', 'clinic', 'doctor', 'nurse', 'medicine',
                'afya', 'hospitali', 'daktari', 'treatment', 'patient', 'medical',
                'dispensary', 'pharmacy', 'drug', 'vaccine', 'immunization'
            ],
            'education': [
                'school', 'teacher', 'student', 'education', 'classroom', 'books',
                'shule', 'mwalimu', 'mwanafunzi', 'elimu', 'fees', 'uniform',
                'exam', 'grade', 'university', 'college', 'learning'
            ],
            'security': [
                'police', 'security', 'crime', 'theft', 'robbery', 'safety',
                'polisi', 'usalama', 'wizi', 'unyangavu', 'askari', 'patrol',
                'violence', 'gang', 'drugs', 'murder', 'assault'
            ],
            'corruption': [
                'corruption', 'bribe', 'kickback', 'fraud', 'embezzlement',
                'rushwa', 'hongo', 'steal', 'misuse', 'accountability',
                'transparency', 'audit', 'procurement'
            ],
            'environment': [
                'environment', 'pollution', 'waste', 'garbage', 'recycling',
                'mazingira', 'uchafuzi', 'taka', 'forest', 'tree', 'climate',
                'air', 'noise', 'dumping', 'conservation'
            ]
        }

        # Sentiment keywords for better local context
        self.positive_indicators = [
            'good', 'excellent', 'great', 'satisfied', 'happy', 'improved',
            'nzuri', 'safi', 'poa', 'vizuri', 'furaha', 'raha'
        ]

        self.negative_indicators = [
            'bad', 'terrible', 'awful', 'disappointed', 'angry', 'frustrated',
            'mbaya', 'haya', 'hasira', 'uchungu', 'vibaya'
        ]

    def process_feedback(self, feedback_id):
        """Enhanced feedback processing with better NLP"""
        try:
            feedback = UserFeedback.query.get(feedback_id)
            if not feedback or not feedback.content:
                logger.warning(f"No feedback found or empty content for ID: {feedback_id}")
                return

            text = feedback.content.lower().strip()

            # Enhanced sentiment analysis
            sentiment_score = self._analyze_sentiment(text)
            feedback.sentiment_score = sentiment_score

            # Enhanced categorization
            categories = self._categorize_feedback(text)
            feedback.tags = categories

            # Extract location mentions if not provided
            if not feedback.location:
                extracted_location = self._extract_location(text)
                if extracted_location:
                    feedback.location = extracted_location

            # Mark as processed
            feedback.is_processed = True

            db.session.commit()
            logger.info(f"Processed feedback {feedback_id}: sentiment={sentiment_score:.2f}, categories={categories}")

        except Exception as e:
            logger.error(f"Error processing feedback {feedback_id}: {str(e)}")
            db.session.rollback()

    def _analyze_sentiment(self, text):
        """Enhanced sentiment analysis combining multiple approaches"""
        try:
            # Use TextBlob for basic sentiment
            blob = TextBlob(text)
            base_sentiment = blob.sentiment.polarity

            # Adjust based on local positive/negative indicators
            positive_count = sum(1 for word in self.positive_indicators if word in text)
            negative_count = sum(1 for word in self.negative_indicators if word in text)

            # Calculate adjustment factor
            adjustment = (positive_count - negative_count) * 0.1

            # Combine scores
            final_sentiment = max(-1.0, min(1.0, base_sentiment + adjustment))

            return final_sentiment

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return 0.0

    def _categorize_feedback(self, text):
        """Enhanced categorization using keyword matching and scoring"""
        categories = []
        category_scores = {}

        # Count keyword matches for each category
        words = re.findall(r'\b\w+\b', text.lower())
        word_set = set(words)

        for category, keywords in self.category_keywords.items():
            matches = len(word_set.intersection(set(keywords)))
            if matches > 0:
                # Score based on number of matches and keyword relevance
                score = matches / len(keywords)
                category_scores[category] = score

        # Select categories with significant scores
        threshold = 0.02  # Adjust this threshold as needed
        categories = [cat for cat, score in category_scores.items() if score >= threshold]

        # If no categories found, try to infer from common patterns
        if not categories:
            categories = self._infer_category_from_patterns(text)

        return categories[:3]  # Limit to top 3 categories

    def _infer_category_from_patterns(self, text):
        """Infer categories from common complaint patterns"""
        categories = []

        # Pattern-based inference
        if any(phrase in text for phrase in ['not working', 'broken', 'damaged', 'needs repair']):
            if any(word in text for word in ['road', 'street', 'bridge']):
                categories.append('infrastructure')
            elif any(word in text for word in ['water', 'pipe', 'tap']):
                categories.append('water_supply')

        if any(phrase in text for phrase in ['lack of', 'shortage', 'unavailable', 'missing']):
            if any(word in text for word in ['medicine', 'doctor', 'treatment']):
                categories.append('healthcare')
            elif any(word in text for word in ['teacher', 'books', 'classroom']):
                categories.append('education')

        return categories

    def _extract_location(self, text):
        """Extract location mentions from text"""
        # Common Kenyan locations and administrative units
        kenyan_locations = [
            'nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'thika', 'malindi',
            'kitale', 'garissa', 'kakamega', 'nyeri', 'machakos', 'meru', 'embu',
            'county', 'ward', 'constituency', 'sub-county', 'location', 'village'
        ]

        words = text.lower().split()
        for i, word in enumerate(words):
            if word in kenyan_locations:
                # Try to get the specific location name
                if word in ['county', 'ward', 'constituency'] and i > 0:
                    return f"{words[i-1].title()} {word.title()}"
                elif word in kenyan_locations[:14]:  # Major cities
                    return word.title()

        return None

    def get_feedback_statistics(self, days=30):
        """Get statistics about processed feedback"""
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_feedback = UserFeedback.query.filter(
            UserFeedback.created_at >= cutoff_date,
            UserFeedback.is_processed == True
        ).all()

        if not recent_feedback:
            return {}

        # Calculate statistics
        sentiments = [f.sentiment_score for f in recent_feedback if f.sentiment_score is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Category distribution
        all_categories = []
        for f in recent_feedback:
            if f.tags:
                all_categories.extend(f.tags)

        category_counts = Counter(all_categories)

        # Location distribution
        locations = [f.location for f in recent_feedback if f.location]
        location_counts = Counter(locations)

        return {
            'total_feedback': len(recent_feedback),
            'average_sentiment': round(avg_sentiment, 3),
            'sentiment_distribution': {
                'positive': len([s for s in sentiments if s > 0.1]),
                'neutral': len([s for s in sentiments if -0.1 <= s <= 0.1]),
                'negative': len([s for s in sentiments if s < -0.1])
            },
            'top_categories': dict(category_counts.most_common(10)),
            'top_locations': dict(location_counts.most_common(10))
        }

# Usage function
def process_feedback(feedback_id):
    """Main function to process feedback - replaces the old one"""
    processor = EnhancedNLPProcessor()
    processor.process_feedback(feedback_id)
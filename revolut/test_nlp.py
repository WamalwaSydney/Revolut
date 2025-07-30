# standalone_nlp_test.py - Test NLP without Flask dependencies
import re
from collections import Counter

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    print("⚠️  TextBlob not installed. Run: pip install textblob")

class StandaloneNLPProcessor:
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
            'nzuri', 'safi', 'poa', 'vizuri', 'furaha', 'raha', 'better', 'working'
        ]

        self.negative_indicators = [
            'bad', 'terrible', 'awful', 'disappointed', 'angry', 'frustrated',
            'mbaya', 'haya', 'hasira', 'uchungu', 'vibaya', 'broken', 'dirty', 'not working'
        ]

    def analyze_sentiment(self, text):
        """Enhanced sentiment analysis"""
        try:
            if HAS_TEXTBLOB:
                # Use TextBlob for basic sentiment
                blob = TextBlob(text)
                base_sentiment = blob.sentiment.polarity
            else:
                # Fallback: simple keyword-based sentiment
                base_sentiment = 0.0

            # Adjust based on local positive/negative indicators
            text_lower = text.lower()
            positive_count = sum(1 for word in self.positive_indicators if word in text_lower)
            negative_count = sum(1 for word in self.negative_indicators if word in text_lower)

            # Calculate adjustment factor
            adjustment = (positive_count - negative_count) * 0.2

            # Combine scores
            final_sentiment = max(-1.0, min(1.0, base_sentiment + adjustment))

            return final_sentiment

        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return 0.0

    def categorize_feedback(self, text):
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
            categories = self.infer_category_from_patterns(text)

        return categories[:3]  # Limit to top 3 categories

    def infer_category_from_patterns(self, text):
        """Infer categories from common complaint patterns"""
        categories = []
        text_lower = text.lower()

        # Pattern-based inference
        if any(phrase in text_lower for phrase in ['not working', 'broken', 'damaged', 'needs repair']):
            if any(word in text_lower for word in ['road', 'street', 'bridge']):
                categories.append('infrastructure')
            elif any(word in text_lower for word in ['water', 'pipe', 'tap']):
                categories.append('water_supply')

        if any(phrase in text_lower for phrase in ['lack of', 'shortage', 'unavailable', 'missing']):
            if any(word in text_lower for word in ['medicine', 'doctor', 'treatment']):
                categories.append('healthcare')
            elif any(word in text_lower for word in ['teacher', 'books', 'classroom']):
                categories.append('education')

        return categories

    def extract_location(self, text):
        """Extract location mentions from text"""
        # Common Kenyan locations and administrative units
        kenyan_locations = [
            'nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'thika', 'malindi',
            'kitale', 'garissa', 'kakamega', 'nyeri', 'machakos', 'meru', 'embu',
            'kibera', 'westlands', 'eastlands', 'karen', 'kilifi', 'lamu'
        ]

        admin_units = ['county', 'ward', 'constituency', 'sub-county', 'location', 'village']

        words = text.lower().split()
        for i, word in enumerate(words):
            # Check for major cities/areas
            if word in kenyan_locations:
                return word.title()

            # Check for administrative units with preceding location name
            if word in admin_units and i > 0:
                return f"{words[i-1].title()} {word.title()}"

        return None

def test_nlp_processor():
    """Test the NLP processor with sample feedback texts"""
    processor = StandaloneNLPProcessor()

    # Test cases covering different scenarios
    test_cases = [
        {
            "text": "The water supply in Kibera is terrible. Pipes are broken and we have no clean water for days.",
            "expected_categories": ["water_supply"],
            "expected_sentiment": "negative"
        },
        {
            "text": "Barabara za Nairobi ni mbaya sana. Pothole nyingi na hakuna repairs.",
            "expected_categories": ["infrastructure"],
            "expected_sentiment": "negative"
        },
        {
            "text": "The new hospital in Nakuru County is excellent. Doctors are very helpful and medicine is available.",
            "expected_categories": ["healthcare"],
            "expected_sentiment": "positive"
        },
        {
            "text": "Shule yetu haina vitabu na mwalimu hawako. Watoto hawajafunza vizuri.",
            "expected_categories": ["education"],
            "expected_sentiment": "negative"
        },
        {
            "text": "Police response in Westlands is good. They patrol regularly and community feels safe.",
            "expected_categories": ["security"],
            "expected_sentiment": "positive"
        },
        {
            "text": "Corruption in procurement is a big problem. Officials demand bribes for everything.",
            "expected_categories": ["corruption"],
            "expected_sentiment": "negative"
        },
        {
            "text": "The environment in Mombasa is polluted. Too much garbage dumping and no recycling.",
            "expected_categories": ["environment"],
            "expected_sentiment": "negative"
        }
    ]

    print("=== Testing Standalone NLP Processor ===\n")
    print(f"TextBlob available: {HAS_TEXTBLOB}")
    print("-" * 50)

    for i, test_case in enumerate(test_cases, 1):
        text = test_case["text"]
        print(f"Test {i}: {text}")

        # Test sentiment analysis
        sentiment_score = processor.analyze_sentiment(text)
        sentiment_label = "positive" if sentiment_score > 0.1 else "negative" if sentiment_score < -0.1 else "neutral"

        # Test categorization
        categories = processor.categorize_feedback(text)

        # Test location extraction
        location = processor.extract_location(text)

        print(f"  Sentiment: {sentiment_score:.3f} ({sentiment_label})")
        print(f"  Categories: {categories}")
        print(f"  Location: {location}")
        print(f"  Expected Sentiment: {test_case['expected_sentiment']}")
        print(f"  Expected Categories: {test_case['expected_categories']}")

        # Check if results match expectations
        sentiment_correct = (
            (test_case['expected_sentiment'] == 'positive' and sentiment_score > 0.1) or
            (test_case['expected_sentiment'] == 'negative' and sentiment_score < -0.1) or
            (test_case['expected_sentiment'] == 'neutral' and -0.1 <= sentiment_score <= 0.1)
        )

        categories_correct = any(cat in categories for cat in test_case['expected_categories'])

        print(f"  ✅ Sentiment: {'Correct' if sentiment_correct else 'Incorrect'}")
        print(f"  ✅ Categories: {'Correct' if categories_correct else 'Incorrect'}")
        print("-" * 50)

    print("\n=== Testing Edge Cases ===\n")

    # Test edge cases
    edge_cases = [
        "",  # Empty string
        "Hello",  # Very short text
        "The road is good but water supply is bad",  # Mixed sentiment
        "This is just a random text with no civic issues",  # No clear category
    ]

    for text in edge_cases:
        print(f"Edge case: '{text}'")
        if text:  # Skip empty string processing
            sentiment = processor.analyze_sentiment(text)
            categories = processor.categorize_feedback(text)
            location = processor.extract_location(text)

            print(f"  Sentiment: {sentiment:.3f}")
            print(f"  Categories: {categories}")
            print(f"  Location: {location}")
        else:
            print("  Skipped empty string")
        print("-" * 30)

def test_keyword_coverage():
    """Test keyword coverage for different categories"""
    processor = StandaloneNLPProcessor()

    print("=== Keyword Coverage Test ===\n")

    for category, keywords in processor.category_keywords.items():
        print(f"{category}: {len(keywords)} keywords")
        print(f"  Sample: {keywords[:5]}")

    print(f"\nPositive indicators: {len(processor.positive_indicators)}")
    print(f"Negative indicators: {len(processor.negative_indicators)}")

if __name__ == "__main__":
    try:
        test_keyword_coverage()
        test_nlp_processor()
        print("\n✅ All NLP tests completed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
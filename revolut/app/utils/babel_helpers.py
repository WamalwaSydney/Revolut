from flask_babel import gettext, ngettext, lazy_gettext
from flask import current_app

def get_available_languages():
    return current_app.config['LANGUAGES']

def get_current_language():
    return session.get('language', 'en')

# Template filters
@app.template_filter('translate_status')
def translate_status(status):
    translations = {
        'en': {
            'Open': 'Open',
            'In Progress': 'In Progress',
            'Resolved': 'Resolved',
            'Closed': 'Closed'
        },
        'sw': {
            'Open': 'Wazi',
            'In Progress': 'Inaendelea',
            'Resolved': 'Imetatuliwa',
            'Closed': 'Imefungwa'
        }
    }
    lang = get_current_language()
    return translations.get(lang, {}).get(status, status)

@app.template_filter('translate_category')
def translate_category(category):
    translations = {
        'en': {
            'Education': 'Education',
            'Health': 'Health',
            'Infrastructure': 'Infrastructure',
            'Water': 'Water',
            'Security': 'Security',
            'Environment': 'Environment'
        },
        'sw': {
            'Education': 'Elimu',
            'Health': 'Afya',
            'Infrastructure': 'Miundombinu',
            'Water': 'Maji',
            'Security': 'Usalama',
            'Environment': 'Mazingira'
        }
    }
    lang = get_current_language()
    return translations.get(lang, {}).get(category, category)
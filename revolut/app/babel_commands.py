import os
import sys

def extract_messages():
    """Extract messages for translation"""
    os.system('pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .')

def init_language(lang):
    """Initialize new language"""
    os.system(f'pybabel init -i messages.pot -d app/translations -l {lang}')

def update_translations():
    """Update existing translations"""
    os.system('pybabel update -i messages.pot -d app/translations')

def compile_translations():
    """Compile translations"""
    os.system('pybabel compile -d app/translations')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python babel_commands.py <command>')
        print('Commands: extract, init <lang>, update, compile')

    command = sys.argv[1]
    if command == 'extract':
        extract_messages()
    elif command == 'init' and len(sys.argv) == 3:
        init_language(sys.argv[2])
    elif command == 'update':
        update_translations()
    elif command == 'compile':
        compile_translations()
#!/bin/bash

# Deployment script for Revolut & WDO platform
# Usage: bash deploy_revolut_wdo.sh

echo "Starting deployment of Revolut & WDO platform..."

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip postgresql postgresql-contrib libpq-dev python3-dev

# Install Python packages
echo "Installing Python dependencies..."
pip3 install flask fastapi sqlalchemy psycopg2-binary nltk python-dotenv gunicorn twilio africastalking pycryptodome

# Set up PostgreSQL
echo "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE revolut_wdo;"
sudo -u postgres psql -c "CREATE USER revolut_user WITH PASSWORD 'securepassword123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE revolut_wdo TO revolut_user;"

# Download NLTK data
echo "Downloading NLTK data..."
python3 -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon'); nltk.download('stopwords')"

# Create project structure
echo "Creating project structure..."
mkdir -p app/{static,templates} config migrations

# Create environment file
echo "Creating environment configuration..."
cat > .env <<EOL
DATABASE_URL=postgresql://revolut_user:securepassword123@localhost/revolut_wdo
SECRET_KEY=your-secret-key-here
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
AFRICASTALKING_API_KEY=your-at-key
EOL

# Create requirements file
echo "Creating requirements.txt..."
cat > requirements.txt <<EOL
flask==2.3.2
fastapi==0.95.2
sqlalchemy==2.0.15
psycopg2-binary==2.9.6
nltk==3.8.1
python-dotenv==1.0.0
gunicorn==20.1.0
twilio==8.4.0
africastalking==4.0.0
pycryptodome==3.18.0
EOL

# Create basic Flask app structure
echo "Creating Flask app structure..."
cat > app/__init__.py <<EOL
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import nltk
from cryptography.fernet import Fernet
import os

db = SQLAlchemy()
migrate = Migrate()
nlp = nltk
fernet = Fernet(os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode()))

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    return app
EOL

echo "Deployment setup complete!"
echo "To start the application:"
echo "1. Run 'flask db init' to initialize migrations"
echo "2. Run 'flask db migrate' and 'flask db upgrade' to setup database"
echo "3. Start the server with 'gunicorn -w 4 'app:create_app()'"

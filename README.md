# Revolut Project

This is a Flask-based web application with PostgreSQL database backend. The project includes user roles, authentication, and various features managed via a web interface.

## Prerequisites

- Python 3.x (preferably 3.8 or higher)
- PostgreSQL database server
- Git (to clone the repository)

## Setup Instructions

1. **Clone the repository**

```bash
git clone (https://github.com/WamalwaSydney/Revolut.git)
cd Revolut\revolut
```

2. **Create and activate a virtual environment**

On Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set environment variables**

Create a `.env` file in the project root or set environment variables in your shell. Required variables:

```env
SECRET_KEY=your_secret_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/your_database_name
ENCRYPTION_KEY=your_encryption_key_here
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@revolut.rw
AFRICASTALKING_USERNAME=your_africastalking_username
AFRICASTALKING_API_KEY=your_africastalking_api_key
SMS_SHORTCODE=your_sms_shortcode
NLTK_DATA_PATH=/path/to/nltk_data  # optional, defaults to ~/nltk_data
PORT=5000  # optional, defaults to 5000
```

Make sure your PostgreSQL database is created and accessible via the `DATABASE_URL`.

## Database Setup

1. **Run database migrations**

```bash
flask db upgrade
```

or if you don't have the flask CLI set up, you can run migrations via your preferred method.

2. **Initialize database with default data**

You can run either of the following scripts to create default roles and admin user:

```bash
python create_initial_data.py
```

or

```bash
python seed.py
```

## Running the Application

Run the app locally with:

```bash
python run.py
```

The app will start on `http://0.0.0.0:5000` by default or on the port specified by the `PORT` environment variable.

## Running Tests

Run tests using pytest:

```bash
pytest
```

Make sure your virtual environment is activated and dependencies are installed.

## Production Notes

- Use `gunicorn` to serve the app in production:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

- Ensure all environment variables are set securely in your production environment.

- The app binds to `0.0.0.0` to be accessible externally.

---

Admin Credentials
username: admin
password: admin123

This README provides all necessary steps to set up, run, and test the Revolut project. For any issues, please check the project documentation or contact the maintainers.

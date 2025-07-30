#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy.exc import ProgrammingError
from werkzeug.security import generate_password_hash
from datetime import datetime

# Get DB connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in environment variables.")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

with engine.connect() as connection:
    # Step 1: Add the missing column `tags` to `user_feedback`
    try:
        connection.execute(text("ALTER TABLE user_feedback ADD COLUMN tags TEXT;"))
        print("✅ Added 'tags' column to user_feedback.")
    except ProgrammingError as e:
        if 'already exists' in str(e):
            print("ℹ️ 'tags' column already exists. Skipping.")
        else:
            raise e
    
    # Step 2: Insert admin user into `user` table
    try:
        result = connection.execute(
            text("SELECT * FROM \"user\" WHERE username = :username"),
            {"username": "admin"}
        )
        if result.first():
            print("ℹ️ Admin user already exists. Skipping.")
        else:
            hashed_password = generate_password_hash("admin123")
            current_time = datetime.utcnow()
            connection.execute(
                text("""
                    INSERT INTO "user" (username, email, password_hash, active, created_at, language) 
                    VALUES (:username, :email, :password_hash, :active, :created_at, :language)
                """),
                {
                    "username": "admin",
                    "email": "admin@revolutwdo.org", 
                    "password_hash": hashed_password,
                    "active": True,
                    "created_at": current_time,
                    "language": "en"
                }
            )
            print("✅ Admin user created with username='admin', password='admin123', and email='admin@revolutwdo.org'.")
    except Exception as e:
        print(f"❌ Failed to insert admin user: {e}")
    
    # Commit the transaction
    connection.commit()
    print("🎉 Database seeding completed successfully!")

# migration_fix_polls.py - Run this script to fix existing poll data
"""
Database migration script to fix existing polls that don't have proper option IDs

Usage:
1. Save this as migration_fix_polls.py in your project root
2. Run: python migration_fix_polls.py
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Poll
from sqlalchemy.orm.attributes import flag_modified

def fix_poll_options_format(poll):
    """Fix poll options format to ensure they have proper IDs"""
    if not isinstance(poll.options, list):
        poll.options = []
        return poll

    fixed_options = []
    for i, option in enumerate(poll.options):
        if isinstance(option, dict):
            # Ensure the option has an ID
            if 'id' not in option:
                option['id'] = i + 1
            # Ensure it has a votes count
            if 'votes' not in option:
                option['votes'] = 0
            # Ensure it has text
            if 'text' not in option:
                option['text'] = f"Option {i + 1}"
            fixed_options.append(option)
        elif isinstance(option, str):
            # Convert string option to dict format
            fixed_options.append({
                'id': i + 1,
                'text': option,
                'votes': 0
            })

    poll.options = fixed_options
    return poll

def main():
    """Main migration function"""
    app = create_app()

    with app.app_context():
        print("Starting poll migration...")

        try:
            # Get all polls
            all_polls = Poll.query.all()
            print(f"Found {len(all_polls)} polls to check")

            fixed_count = 0
            for poll in all_polls:
                print(f"\nChecking poll {poll.id}: {poll.question[:50]}...")
                print(f"Current options: {poll.options}")

                original_options = poll.options
                poll = fix_poll_options_format(poll)

                # Check if anything changed
                if poll.options != original_options:
                    flag_modified(poll, "options")
                    fixed_count += 1
                    print(f"✓ Fixed poll {poll.id}")
                    print(f"  New options: {poll.options}")
                else:
                    print(f"  Poll {poll.id} already has correct format")

            if fixed_count > 0:
                print(f"\nCommitting changes for {fixed_count} polls...")
                db.session.commit()
                print("✓ Migration completed successfully!")
            else:
                print("\n✓ No polls needed fixing")

            print(f"\nSummary:")
            print(f"  Total polls: {len(all_polls)}")
            print(f"  Fixed polls: {fixed_count}")

        except Exception as e:
            print(f"✗ Error during migration: {str(e)}")
            db.session.rollback()
            return False

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
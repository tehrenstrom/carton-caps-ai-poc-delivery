# Development Scripts

This directory contains utility scripts for local development.

## Database Seeding

The `seed_database.py` script populates your local database with sample data for development and testing. It uses the application's async API directly, which helps validate that the API works correctly with the database.

### Usage

```bash
# Make sure you're in the project root
cd /path/to/project

# Run the script
python scripts/seed_database.py
```

### What It Does

The seeding script:

1. Creates database tables if they don't already exist
2. Populates the database with sample data:
   - Schools
   - Users (with school associations)
   - Products
   - FAQs for the referral program
   - Referral program rules
   - Sample conversation history

### Benefits of Using Async API for Seeding

Using the application's async API directly for database seeding has several advantages:

1. **Consistency**: The same API used in production is used for seeding, ensuring consistency.
2. **Testing**: Implicitly tests the API endpoints and database access patterns.
3. **Idempotence**: The script is designed to be idempotent - you can run it multiple times without creating duplicates.
4. **Maintenance**: When the data model changes, you only need to update in one place.

## Other Scripts

- `../setup.sh` - Sets up the development environment, including virtualenv creation, dependency installation, and .env file configuration

## Adding New Scripts

When adding new scripts to this directory:

1. Make the script executable: `chmod +x your_script.py`
2. Update this README to document the new script
3. Use the application's API when possible for database interactions 

from app.database import engine, Base
from app import database as models

print("Dropping all tables...")
try:
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped.")
except Exception as e:
    print(f"Error dropping tables: {e}")

print("Creating all tables...")
models.init_db()
print("Database reset complete.")

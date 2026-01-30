
from app.database import SessionLocal
from app.models.document import Document, DocumentPage
from app.models.extraction import ExtractedField, DocumentLine
from app.models.user import User

def cleanup():
    db = SessionLocal()
    try:
        print("Cleaning up database...")
        db.query(DocumentLine).delete()
        db.query(ExtractedField).delete()
        db.query(DocumentPage).delete()
        db.query(Document).delete()
        db.commit()
        print("Cleanup complete.")
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()

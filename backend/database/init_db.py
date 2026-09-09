from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.database.connection import engine, Base, SessionLocal
from backend.models.orm_models import Client, User, Dataset, Report
from backend.utils.auth import get_password_hash
from datetime import datetime

def create_and_seed_tables():
    """Initializes tables and seeds default user and isolated client data in an idempotent way."""
    # 1. Create all missing tables based on ORM definitions
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        print("Running database seeding check...")
        
        # Helper to get or create Client
        client1 = db.query(Client).filter(Client.email == "client1@example.com").first()
        if not client1:
            print("Seeding Client 1 (ABC Technologies)...")
            client1 = Client(
                company_name="ABC Technologies",
                contact_name="Alice Smith",
                email="client1@example.com",
                phone="+1-555-0101",
                industry="Technology",
                plan="PRO",
                status="ACTIVE",
                created_at=datetime.utcnow()
            )
            db.add(client1)
            db.commit()
            db.refresh(client1)
        else:
            print("Client 1 already exists.")

        client2 = db.query(Client).filter(Client.email == "client2@example.com").first()
        if not client2:
            print("Seeding Client 2 (XYZ Corporation)...")
            client2 = Client(
                company_name="XYZ Corporation",
                contact_name="Bob Jones",
                email="client2@example.com",
                phone="+1-555-0202",
                industry="Finance",
                plan="ENTERPRISE",
                status="ACTIVE",
                created_at=datetime.utcnow()
            )
            db.add(client2)
            db.commit()
            db.refresh(client2)
        else:
            print("Client 2 already exists.")

        # Helper to get or create Users
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            print("Seeding Admin User...")
            admin = User(
                name="Platform Admin",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                role="ADMIN",
                client_id=None,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(admin)
            db.commit()
        else:
            print("Admin User already exists.")

        user1 = db.query(User).filter(User.email == "client1@example.com").first()
        if not user1:
            print("Seeding User 1...")
            user1 = User(
                name="Alice Smith",
                email="client1@example.com",
                password_hash=get_password_hash("client123"),
                role="CLIENT",
                client_id=client1.id,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user1)
            db.commit()
        else:
            print("User 1 already exists.")

        user2 = db.query(User).filter(User.email == "client2@example.com").first()
        if not user2:
            print("Seeding User 2...")
            user2 = User(
                name="Bob Jones",
                email="client2@example.com",
                password_hash=get_password_hash("client123"),
                role="CLIENT",
                client_id=client2.id,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(user2)
            db.commit()
        else:
            print("User 2 already exists.")

        # 3. Copy existing 'sales' table data into isolated client tables
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        if "sales" in table_names:
            # Seeding for client 1
            c1_table = f"dataset_client_{client1.id}_seed"
            if c1_table not in table_names:
                print(f"Creating isolated seed dataset table {c1_table} from sales...")
                db.execute(text(f"CREATE TABLE `{c1_table}` AS SELECT * FROM sales"))
                db.commit()
                
                row_count = db.execute(text(f"SELECT COUNT(*) FROM `{c1_table}`")).scalar()
                cols = inspector.get_columns("sales")
                col_count = len(cols)
                
                dataset1 = Dataset(
                    client_id=client1.id,
                    name="ABC Technologies Seed Dataset",
                    filename="sales_data.csv",
                    table_name=c1_table,
                    row_count=row_count,
                    col_count=col_count,
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                )
                db.add(dataset1)
                db.commit()
            else:
                print(f"Table {c1_table} already exists.")

            # Seeding for client 2
            c2_table = f"dataset_client_{client2.id}_seed"
            if c2_table not in table_names:
                print(f"Creating isolated seed dataset table {c2_table} from sales...")
                db.execute(text(f"CREATE TABLE `{c2_table}` AS SELECT * FROM sales"))
                db.commit()
                
                row_count = db.execute(text(f"SELECT COUNT(*) FROM `{c2_table}`")).scalar()
                cols = inspector.get_columns("sales")
                col_count = len(cols)
                
                dataset2 = Dataset(
                    client_id=client2.id,
                    name="XYZ Corporation Seed Dataset",
                    filename="sales_data.csv",
                    table_name=c2_table,
                    row_count=row_count,
                    col_count=col_count,
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                )
                db.add(dataset2)
                db.commit()
            else:
                print(f"Table {c2_table} already exists.")
        else:
            print("Warning: 'sales' table not found in business.db. Isolation seed datasets skipped.")

        print("Database seeding check completed successfully!")
            
    except Exception as e:
        db.rollback()
        print(f"Error during database seeding: {str(e)}")
    finally:
        db.close()

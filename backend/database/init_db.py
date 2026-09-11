import os
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
import pandas as pd

from backend.database.connection import engine, Base, SessionLocal, PROJECT_ROOT, quote_ident
from backend.models.orm_models import Client, User, Dataset, Report
from backend.utils.auth import get_password_hash

logger = logging.getLogger("ai_analyst.init_db")


def create_and_seed_tables():
    """
    Initializes tables and seeds default users and isolated client data in an idempotent way.
    Ensures that on fresh deployments (e.g. Render Linux), the database schema, primary 'sales' table,
    and isolated client seed tables are fully populated automatically.
    """
    logger.info("[Database Init] Verifying tables and schema definitions...")
    # 1. Create all missing tables based on ORM definitions (clients, users, datasets, reports)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        logger.info("[Database Init] Running database seeding check...")
        
        # 2. Check and seed default Clients
        client1 = db.query(Client).filter(Client.email == "client1@example.com").first()
        if not client1:
            logger.info("[Database Init] Seeding Client 1 (ABC Technologies)...")
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
            logger.debug("[Database Init] Client 1 already exists.")

        client2 = db.query(Client).filter(Client.email == "client2@example.com").first()
        if not client2:
            logger.info("[Database Init] Seeding Client 2 (XYZ Corporation)...")
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
            logger.debug("[Database Init] Client 2 already exists.")

        # 3. Check and seed Users
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            logger.info("[Database Init] Seeding Admin User...")
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
            logger.debug("[Database Init] Admin User already exists.")

        user1 = db.query(User).filter(User.email == "client1@example.com").first()
        if not user1:
            logger.info("[Database Init] Seeding User 1...")
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
            logger.debug("[Database Init] User 1 already exists.")

        user2 = db.query(User).filter(User.email == "client2@example.com").first()
        if not user2:
            logger.info("[Database Init] Seeding User 2...")
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
            logger.debug("[Database Init] User 2 already exists.")

        # 4. Check for 'sales' table; populate from sales_data.csv if missing (fresh deployment)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        if "sales" not in table_names:
            csv_candidates = [
                PROJECT_ROOT / "sales_data.csv",
                Path("sales_data.csv").resolve(),
            ]
            csv_path = next((p for p in csv_candidates if p.is_file()), None)
            if csv_path:
                logger.info(f"[Database Init] Populating 'sales' table from {csv_path}...")
                print(f"[Database Init] Populating 'sales' table from {csv_path}...")
                df = pd.read_csv(csv_path)
                df.to_sql("sales", engine, if_exists="replace", index=False)
                logger.info(f"[Database Init] Successfully created 'sales' table with {len(df)} records.")
                # Refresh table names list
                inspector = inspect(engine)
                table_names = inspector.get_table_names()
            else:
                logger.warning("[Database Init] sales_data.csv not found; 'sales' table could not be auto-seeded.")

        # 5. Populate isolated client seed tables from 'sales' table
        if "sales" in table_names:
            # Client 1 isolated seed dataset
            c1_table = f"dataset_client_{client1.id}_seed"
            if c1_table not in table_names:
                logger.info(f"[Database Init] Creating isolated seed dataset {c1_table} from sales...")
                quoted_c1 = quote_ident(c1_table)
                quoted_sales = quote_ident("sales")
                db.execute(text(f"CREATE TABLE {quoted_c1} AS SELECT * FROM {quoted_sales}"))
                db.commit()
                
                row_count = db.execute(text(f"SELECT COUNT(*) FROM {quoted_c1}")).scalar()
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
                logger.debug(f"[Database Init] Table {c1_table} already exists.")

            # Client 2 isolated seed dataset
            c2_table = f"dataset_client_{client2.id}_seed"
            if c2_table not in table_names:
                logger.info(f"[Database Init] Creating isolated seed dataset {c2_table} from sales...")
                quoted_c2 = quote_ident(c2_table)
                quoted_sales = quote_ident("sales")
                db.execute(text(f"CREATE TABLE {quoted_c2} AS SELECT * FROM {quoted_sales}"))
                db.commit()
                
                row_count = db.execute(text(f"SELECT COUNT(*) FROM {quoted_c2}")).scalar()
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
                logger.debug(f"[Database Init] Table {c2_table} already exists.")
        else:
            logger.warning("[Database Init] 'sales' table not found; isolation seed datasets skipped.")

        logger.info("[Database Init] Database verification and seeding completed successfully!")
        print("[Database Init] Database verification and seeding completed successfully.")
            
    except Exception as e:
        db.rollback()
        logger.error(f"[Database Init] Error during database seeding: {str(e)}", exc_info=True)
        print(f"[Database Init] Error during database seeding: {str(e)}")
    finally:
        db.close()

# from app.database import Base, engine
# from app.models import User


# print("Creating database tables...")

# Base.metadata.create_all(bind=engine)

# print("Tables created successfully.")


from app.database import Base, engine

# Import all models so SQLAlchemy knows which tables to create.
from app.models import (
    User,
    WorkProcess,
    WorkStep,
    EmployeeProgress,
)


def create_tables():
    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully.")


if __name__ == "__main__":
    create_tables()
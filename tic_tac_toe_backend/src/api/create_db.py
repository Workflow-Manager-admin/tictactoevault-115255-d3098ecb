"""Utility to create tables for Tic Tac Toe backend."""

from .db import Base, engine


def main():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")


if __name__ == "__main__":
    main()

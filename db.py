
import os

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "guess_number_db")
        )

        return connection

    except Error as error:
        print("Database connection failed:", error)
        return None


if __name__ == "__main__":
    connection = get_db_connection()

    if connection is not None and connection.is_connected():
        print("MySQL connection successful!")
        print("Connected to the configured database.")
        connection.close()
    else:
        print("Could not connect to MySQL.")

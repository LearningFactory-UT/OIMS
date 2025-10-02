import sqlite3

def empty_database(db_path):
    try:
        # Connect to the SQLite database
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Get the list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        # Iterate through the tables and delete all records
        for table in tables:
            table_name = table[0]
            if table_name != 'sqlite_sequence':  # Skip the SQLite sequence table (used for AUTOINCREMENT)
                cursor.execute(f"DELETE FROM {table_name};")

        # Commit changes and close the connection
        connection.commit()
        print("All tables have been emptied successfully.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    # Path to your SQLite database file
    database_path = "my_persistent_data.db"

    # Empty the database
    empty_database(database_path)

import sqlite3

# Connect to SQLite database (if it doesn't exist, it will be created)
conn = sqlite3.connect('database.db')

# Create a cursor object
cursor = conn.cursor()

# Create a 'restaurants' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone_number TEXT,
    cuisine_type TEXT
)
''')

# Insert sample data into the table
cursor.execute('''
INSERT INTO restaurants (name, address, phone_number, cuisine_type)
VALUES ('Restaurant A', '123 Main St, Cityville', '123-456-7890', 'Italian')
''')

cursor.execute('''
INSERT INTO restaurants (name, address, phone_number, cuisine_type)
VALUES ('Restaurant B', '456 Elm St, Townsville', '987-654-3210', 'Chinese')
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database and table created successfully!")

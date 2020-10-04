import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

class Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
    
    def execute(self, query):
        try:
            self.cursor.execute(query)
        except:
            self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            self.cursor = Cursor(self.conn)
            self.cursor.execute(query)
        
    def fetchone(self):
        return self.cursor.fetchone()
    
    def fetchall(self):
        return self.cursor.fetchall()

class Connection:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        self.cursor = Cursor(self.conn)

    def commit(self):
        self.conn.commit()
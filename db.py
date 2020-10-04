import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

class Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
    
    def execute(self, query):
        try:
            return self.cursor.execute(query)
        except:
            self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            self.cursor = Cursor(self.conn)
            return self.cursor.execute(query)
        
    def fetchone():
        return self.cursor.fetchone()
    
    def fetchall():
        return self.cursor.fetchall()

class Connection:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        self.cursor = Cursor(self.conn)
    
    def commit(self):
        self.conn.commit()
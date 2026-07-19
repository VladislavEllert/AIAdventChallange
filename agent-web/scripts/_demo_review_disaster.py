"""Demo module for day-32 AI review video — deliberately packed with obvious
bugs to show off the review bot. Throwaway file, deleted after recording."""
import sqlite3

API_KEY = "sk-proxyapi-super-secret-hardcoded-key-1234567890"


def get_user(db_path: str, username: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # SQL injection: username interpolated straight into the query
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cur.execute(query)
    return cur.fetchone()


def add_item(item, bucket=[]):
    # mutable default argument — bucket is shared across every call
    bucket.append(item)
    return bucket


def process_all(items):
    for i in range(len(items) + 1):
        # off-by-one: will IndexError on the last iteration
        print(items[i])


def read_log(path):
    f = open(path)
    data = f.read()
    try:
        return int(data)
    except:
        pass


def wait_forever(flag):
    while flag == True:
        pass

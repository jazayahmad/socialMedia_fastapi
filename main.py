from time import time
from aio_pika import author_info
from fastapi import FastAPI, Response, status, HTTPException, Depends
from fastapi.params import Body
from random import randrange
from httpx import post
import psycopg2
from psycopg2.extras import RealDictCursor
import time


from sqlalchemy.orm import Session
import models, schemas, utils
from database import engine, get_db
from routers import posts, users, auth

models.Base.metadata.create_all(bind=engine)



app = FastAPI()

while True:
    try:
        conn = psycopg2.connect(host='localhost', database='fastapi',
                                user='postgres', password='hellojee',
                                cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        print("DB connection was Success")
        break
    except Exception as error:
        print("Conneting to DB failed")
        print("Error: ", error)
        time.sleep(3)

my_post = [{"title": "Title of Post#1", "content": "This is your first post", "id":1}, {"title": "Title of Post#2", "content": "This is your 2nd post", "id":2}]

def find_post(id):
    for p in my_post:
        if p["id"] == id:
            return p

def find_index_post(id):
    for i, p in enumerate(my_post):
        if p["id"] == id:
            return i

app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"message":"Hello World"}




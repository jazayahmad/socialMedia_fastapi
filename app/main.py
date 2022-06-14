from fastapi import FastAPI
import models
from database import engine
from routers import posts, users, auth, vote
from fastapi.middleware.cors import CORSMiddleware

#Command that tells SQLAlchemy to run the create statement so that it generates all of the tables when it starts up
models.Base.metadata.create_all(bind=engine)

#A list of origins that should be permitted to make cross-origin requests. E.g. ['https://example.org', 'https://www.example.org']
# origins = ["https://www.google"]
origins = ['*']

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(vote.router)

@app.get("/")
def root():
    return {"message":"Hello World"}




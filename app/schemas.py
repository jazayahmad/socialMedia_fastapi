from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, conint

# API Data Model
class PostBase(BaseModel):
    #required properties
    title: str
    content: str
    published: bool = True

class PostCreate(PostBase):
    pass

# Response Model 
# class Post(PostBase):
#     # properties which will go in Repsonse
#     id: int
#     created_at: datetime
#     owner_id: int
#     owner: UserOut

#     class Config:
#         orm_mode = True

# User's Schema
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# User's Response
class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True

class Post(PostBase):
    # properties which will go in Repsonse
    id: int
    created_at: datetime
    owner_id: int
    owner: UserOut

    class Config:
        orm_mode = True
        

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None

#Scehma for Vote
class Vote(BaseModel):
    post_id: int  
    dir: conint(ge=0, le=1)


class PostOut(BaseModel):
    Post: Post
    votes: int

    class Config:
        orm_mode = True
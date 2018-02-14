import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context

Base = declarative_base()

# Tables:

class User(Base):

    __tablename__ = 'user'

    userId = Column(Integer, primary_key = True)
    userName = Column(String(32), nullable = False)
    userEmail = Column(String(250), nullable = False)
    userPicture = Column(String(250))


class Category(Base):

    __tablename__ = 'category'

    categoryId = Column(Integer, primary_key = True)
    categoryDesc = Column(String(80), nullable = False)
    userId = Column(Integer, ForeignKey('user.userId'))
    userName = relationship(User, backref = "category")

    @property
    def serialize(self):
        return {
            'CategoryId' : self.categoryId,
            'Category' : self.categoryDesc
        }


class Items(Base):

    __tablename__ = 'items'

    itemId = Column(Integer, primary_key = True)
    itemName = Column(String(80), nullable = False)
    itemDesc = Column(String(250))
    categoryId = Column(Integer, ForeignKey('category.categoryId'))
    category = relationship(Category)
    createdDate = Column(DateTime, default = datetime.datetime.utcnow)
    userId = Column(Integer, ForeignKey('user.userId'))
    userName = relationship(User, backref = "items")

    @property
    def serialize(self):
        return {
            'itemId' : self.itemId,
            'itemName' : self.itemName,
            'itemDesc' : self.itemDesc,
            'category' : self.category.categoryDesc
        }


# Create the database
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)

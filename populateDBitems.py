from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catagory, Items

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind = engine)
session = DBSession()

drink1 = Items(itemName = "PowerThirst!", itemDesc = "An explosion of energy.", catagory = catagory3)
session.add(drink1)
session.commit()

print "Added Items to DB"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Items, User

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind = engine)
session = DBSession()

user1 = User(userName = "Jim Bean", userEmail = "jimmybean@jimbean.ca", userPicture = "https://4.bp.blogspot.com/-cDeYCsNL-ZQ/UozsUJ7EqfI/AAAAAAAAGSk/EtuzOVpHoS0/s1600/andy.png")
session.add(user1)
session.commit()

category1 = Category(categoryDesc = "Soft Drinks", userId = 1)
session.add(category1)
session.commit()

drink1 = Items(itemName = "Coke", itemDesc = "A classic.", category = category1, userId = 1)
session.add(drink1)
session.commit()

drink2 = Items(itemName = "Pepsi", itemDesc = "Another, but slightly less, classic.", category = category1, userId = 1)
session.add(drink2)
session.commit()

category2 = Category(categoryDesc = "Sport Drinks", userId = 1)
session.add(category2)
session.commit()

drink3 = Items(itemName = "Gatorade", itemDesc = "Electrolytes in a bottle.", category = category2, userId = 1)
session.add(drink3)
session.commit()

drink4 = Items(itemName = "Poweraid", itemDesc = "Feel good when you feel bad.", category = category2, userId = 1)
session.add(drink4)
session.commit()

category3 = Category(categoryDesc = "Energy Drinks", userId = 1)
session.add(category3)
session.commit()

drink5 = Items(itemName = "PowerThirst!", itemDesc = "An explosion of energy.", category = category3, userId = 1)
session.add(drink5)
session.commit()

drink6 = Items(itemName = "Brawndo", itemDesc = "What if everything you ever wanted came in a rocket can.", category = category3, userId = 1)
session.add(drink6)
session.commit()

print "Added Items to DB"

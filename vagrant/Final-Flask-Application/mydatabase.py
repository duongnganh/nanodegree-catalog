import os, sys

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.sql import func
from sqlalchemy import text
import datetime


Base = declarative_base()

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	email = Column(String(250), nullable=False)
	picture = Column(String(250))

#  all mapped classes should inherit Base
class Restaurant(Base):
	__tablename__ = 'restaurant'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		return {
			'name' : self.name,
			'id' : self.id,
		}

class MenuItem(Base):
	__tablename__ = 'menu_item'

	name = Column(String(80), nullable=False)
	id = Column(Integer, primary_key=True)
	description = Column(String(250))
	price = Column(String(8))
	course = Column(String(250))
	created_date = Column(DateTime, default=datetime.datetime.now())
	restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
	restaurant = relationship(Restaurant)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		return {
			'name' : self.name,
			'id' : self.id,
			'description' : self.description,
			'price' : self.price,
			'restaurant_id' : self.restaurant_id,
			'created_date' : self.created_date,
		}

engine = create_engine('sqlite:///restaurantmenu.db')

Base.metadata.create_all(engine)

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from myapp.models.config import Base
from myapp.models import User, Restaurant
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime
import random
import string
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


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
      'name': self.name,
      'id': self.id,
      'description': self.description,
      'price': self.price,
      'course': self.course,
      'created_date': self.created_date,
      'restaurant_id': self.restaurant_id,
      'user_id': self.user_id
    }

  @staticmethod
  def validate(data):
    errors = []
    required_fields = ['name', 'description', 'price', 'course']
    if type(data) != dict:
      error = dict({"Missing required parameters":" ".format(', '.join(required_fields))})
      errors.append(error)
    else:
      for value in required_fields:
        if not value in data:
          error = dict({ value: "Required" })
          errors.append(error)
        else:
          if not data[value]:
            error = dict({ value: "Required" })
            errors.append(error)
    return errors
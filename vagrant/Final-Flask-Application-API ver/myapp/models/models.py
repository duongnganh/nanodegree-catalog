from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime
import random
import string
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


Base = declarative_base()
secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))

class User(Base):
  __tablename__ = 'user'

  id = Column(Integer, primary_key=True)
  name = Column(String(250), nullable=False)
  email = Column(String(250))
  picture = Column(String(250))
  password_hash = Column(String(64))

  def hash_password(self, password):
    self.password_hash = pwd_context.encrypt(password)

  def verify_password(self, password):
    return pwd_context.verify(password, self.password_hash)

  def generate_auth_token(self, expiration=600):
    s = Serializer(secret_key, expires_in = expiration)
    return s.dumps({'id': self.id })

  @property
  def serialize(self):
    return {
      'name': self.name,
      'id': self.id,
      'email': self.email,
      'picture': self.picture
    }

  @staticmethod
  def validate(data):
      errors = []
      required_fields = ['name', 'email', 'picture']
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


class Restaurant(Base):
  __tablename__ = 'restaurant'

  id = Column(Integer, primary_key=True)
  name = Column(String(250), nullable=False)
  user_id = Column(Integer, ForeignKey('user.id'))
  user = relationship(User)

  @property
  def serialize(self):
    return {
      'name': self.name,
      'id': self.id,
      'user_id': self.user_id
    }

  @staticmethod
  def validate(data):
    errors = []
    required_fields = ['name']
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
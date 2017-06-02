from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from myapp.models.config import Base
from myapp.models import User
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime
import random
import string
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


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
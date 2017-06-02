from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from myapp.models.config import Base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime
import random
import string
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

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
    return []
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
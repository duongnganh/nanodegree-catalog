import datetime
import random
import string

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

Base = declarative_base()


def validate_insertion(data, required_fields):
    errors = []
    if type(data) != dict:
        error = dict({"Missing required parameters":
                     " ".format(', '.join(required_fields))})
        errors.append(error)
        return errors

    for field in required_fields:
        if field not in data or not data[field]:
            error = dict({value: "Required"})
            errors.append(error)


def validate_update(data, possible_fields):
    errors = []
    if type(data) != dict:
        error = dict({"Missing required parameters":
                     " ".format(', '.join(required_fields))})
        errors.append(error)
        return errors

    for field in possible_fields:
        if field in data and not data[field]:
            error = dict({value: "Required"})
            errors.append(error)


from myapp.models.Restaurant import *
from myapp.models.MenuItem import *
from myapp.models.User import *

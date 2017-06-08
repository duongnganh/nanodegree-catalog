import requests
import random
import httplib2
import json
import string

from flask import Flask, render_template, request, redirect, \
                  url_for, jsonify, make_response, abort, g
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from functools import wraps

from myapp.models import *

engine = create_engine('sqlite:///restaurantmenu.db')

Base.metadata.create_all(engine)
Base.metadata.bind = engine
DB_Session = sessionmaker(bind=engine)

session = DB_Session()
app = Flask(__name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.user = None
        if request.headers:
            token = request.headers.get('token')
            if token:
                user_id = User.verify_auth_token(token)
                if user_id:
                    user = session.query(User).filter_by(id=user_id).first()
                    if user:
                        g.user = user
        if not g.user:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(403)
def not_authorized(error):
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)


@app.after_request
def set_response_header(response):
    response.headers['Content-Type'] = 'application/json'
    return response


from myapp.controllers.Restaurant import *
from myapp.controllers.MenuItem import *
from myapp.controllers.User import *

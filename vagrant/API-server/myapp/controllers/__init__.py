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
            token = request.headers.get('Authorization')
            if token:
                user_id = User.verify_auth_token(token)
                if user_id:
                    user = session.query(User).filter_by(id=user_id).first()
                    if user:
                        g.user = user
        if not g.user:
            abort(403, 'Invalid token')
        return f(*args, **kwargs)

    return decorated_function


@app.errorhandler(400)
def bad_request(error):
    if error.description == None:
        return jsonify({'error': 'Not found'}), 400
    return jsonify({'error': error.description}), 400


@app.errorhandler(401)
def unauthorized(error):
    if error.description == None:
        return jsonify({'error': 'Unauthorized access'}), 401
    return jsonify({'error': error.description}), 401


@app.errorhandler(403)
def forbidden(error):
    if error.description == None:
        return jsonify({'error': 'Unauthorized access'}), 403
    return jsonify({'error': error.description}), 403


@app.errorhandler(404)
def not_found(error):
    if error.description == None:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'error': error.description}), 404


@app.errorhandler(409)
def conflict(error):
    if error.description == None:
        return jsonify({'error': 'Request conflict'}), 409
    return jsonify({'error': error.description}), 409


@app.errorhandler(500)
def server_error(error):
    if error.description == None:
        return jsonify({'error': 'Server error'}), 500
    return jsonify({'error': error.description}), 500


@app.after_request
def set_response_header(response):
    response.headers['Content-Type'] = 'application/json'
    return response


from myapp.controllers.Restaurant import *
from myapp.controllers.MenuItem import *
from myapp.controllers.User import *

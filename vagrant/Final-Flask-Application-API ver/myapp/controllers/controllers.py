from flask import Flask, render_template, request, redirect, \
                  url_for, jsonify, make_response, abort, g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from myapp.models.models import Restaurant, MenuItem, User, Base
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from flask import session as login_session
from functools import wraps
import requests
import random
import httplib2
import json
import string

from flask.ext.httpauth import HTTPBasicAuth

# auth = HTTPBasicAuth()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

engine = create_engine('sqlite:///restaurantmenu.db')

Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
app = Flask(__name__)

# Uncomment when clear login_session
@app.route("/reset", methods=["GET", "POST", "PUT", "DELETE"])
def reset():
    login_session.clear()
    return "reseted"


@app.before_request
def before_request():
    try:
        current_user = session.query(User).filter_by(id=login_session["user_id"]).one();
        g.user = current_user
    except:
        g.user = None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return "You must log in. Log in using /login or /api/v1/login"
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def welcome():
    output = '/login\n'
    output += '/logout\n'
    output += '/logout\n'
    return 'Welcome\n'


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/logout')
@login_required
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['name']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        return jsonify(result=True), 201
    else:
        return jsonify({'error':'provider not found'}), 404


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data

    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
          json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps
                                 ('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['name'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    try:
        user = session.query(User).filter_by(email=data["email"]).one()
        user_id = user.id
    except:
        user_id = None

    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return render_template("info.html", name=login_session['name'],
                           picture=login_session['picture'])


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
# ======================================================================================================
@app.route('/api/v1/users', methods= ['POST'])
def new_user():
    if not request.json:
        return jsonify({'error':'invalid json'}), 400
    if not 'name' in request.json or not 'password' in request.json:
        return jsonify({'error':'missing name or password'}), 400
    name = request.json.get('name')
    password = request.json.get('password')
    if not name or not password:
        return jsonify({'error':'missing name or password'}), 400
    if session.query(User).filter_by(name = name).first() is not None:
        return jsonify({'message':'user already exists'}), 409

    user = User(name = name)
    user.hash_password(password)
    session.add(user)
    session.commit()
    token = user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})

@app.route('/api/v1/users', methods=['PUT'])
@login_required
def update_user():
    pass

@app.route('/api/v1/logout', methods = ['GET'])
@login_required
def api_logout():
    g.user = None
    del login_session['name']
    del login_session['user_id']
    return jsonify({"result": True})

@app.route('/api/v1/login', methods = ['POST'])
def api_login():
    if "user_id" in login_session:
        return jsonify({'error':'you must log out before logging in'}), 400
    if not request.json:
        return jsonify({'error':'invalid json'}), 400
    if not 'name' in request.json or not 'password' in request.json:
        return jsonify({'error':'missing name or password'}), 400
    name = request.json.get('name')
    password = request.json.get('password')
    user = session.query(User).filter_by(name = name).first()
    if not user or not user.verify_password(password):
        return jsonify({"result": False})
    token = user.generate_auth_token(6000)
    login_session['name'] = name
    login_session['user_id'] = user.id
    g.user = user
    return jsonify({'token': token.decode('ascii')})

# ===================================================
@app.route('/api/v1/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[r.serialize for r in restaurants])


@app.route('/api/v1/restaurants', methods=['POST'])
@login_required
def new_restaurant():
    if not request.json:
        return jsonify({'error':'invalid json'}), 400
    errors = Restaurant.validate(request.json)

    if len(errors) != 0:
        return jsonify(errors = [error for error in errors]), 400

    restaurant = Restaurant(name=request.json.get('name'),
                            user_id=g.user.id)
    session.add(restaurant)
    session.commit()
    return jsonify(result=True), 201


@app.route('/api/v1/restaurants/<int:restaurant_id>', methods=['PUT'])
@login_required
def edit_restaurant(restaurant_id):
    if not request.json:
        abort(400)

    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    restaurant.name = request.json.get('name')

    session.add(restaurant)
    session.commit()
    return jsonify(result=True), 201


# Delete a restaurant
@app.route('/api/v1/restaurants/<int:restaurant_id>', methods=['DELETE'])
@login_required
def delete_restaurant(restaurant_id):
    if not request.json:
        abort(400)

    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    for i in items:
        session.delete(i)
        session.commit()

    session.delete(restaurant)
    session.commit()
    return jsonify(result=True), 201


@app.route('/api/v1/restaurants/<int:restaurant_id>/menuitems', methods=['GET'])
def get_menuitems(restaurant_id):
    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return jsonify({'error': 'Restaurant not found'}), 404

    items_query = session.query(MenuItem)
    items = items_query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/api/v1/restaurants/<int:restaurant_id>/menuitems', methods=['POST'])
@login_required
def new_menuitem(restaurant_id):
    if not request.json:
        abort(400)
    errors = MenuItem.validate(request.json)

    if len(errors) != 0:
        return jsonify(errors = [error for error in errors]), 400

    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.id != g.user.id:
        abort(403)

    item = MenuItem(name=request.json.get('name'),
                    description=request.json.get('description'),
                    price=request.json.get('price'),
                    course=request.json.get('course'),
                    restaurant_id=restaurant_id,
                    user_id=restaurant.user_id)

    session.add(item)
    session.commit()
    return jsonify(result=True), 201


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['GET'])
def get_menuitem(menu_id):
    try:
        item = session.query(MenuItem).filter_by(id=menu_id).one()
        return jsonify(item=item.serialize)
    except:
        return jsonify({'error': 'Item not found'}), 404


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['PUT'])
@login_required
def edit_menuitem(menu_id):
    if not request.json:
        abort(400)

    try:
        item = session.query(MenuItem).filter_by(id=menu_id).one()
    except:
        return jsonify({'error': 'Item not found'}), 404

    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=item.restaurant_id).one()
    except:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    if request.json.has_key('name'):
        item.name = request.json.get('name')
    if request.json.has_key('description'):
        item.description = request.json.get('description')
    if request.json.has_key('price'):
        item.price = request.json.get('price')
    if request.json.has_key('course'):
        item.course = request.json.get('course')

    session.add(item)
    session.commit()
    return jsonify(result=True), 201


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['DELETE'])
@login_required
def delete_menuitem(menu_id):
    if not request.json:
        abort(400)

    try:
        item = session.query(MenuItem).filter_by(id=menu_id).one()
    except:
        return jsonify({'error': 'Item not found'}), 404

    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=item.restaurant_id).one()
    except:
        return jsonify({'error': 'Restaurant not found'}), 404

    session.delete(item)
    session.commit()
    return jsonify(result=True), 201


@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(403)
def notauthorized(error):
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
            'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

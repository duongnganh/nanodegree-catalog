from flask import Flask, render_template, request, redirect, \
                  url_for, jsonify, make_response
# from initialize_db import session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Restaurant, MenuItem, User
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from flask import session as login_session
import requests
import random
import httplib2
import json
import string

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

# We must specify which db to use
engine = create_engine('sqlite:///restaurantmenu.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.create_all(engine)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Uncomment when clear login_session
# login_session.clear()


# Welcome page
@app.route('/')
@app.route('/restaurants/')
def welcome():
    restaurants = session.query(Restaurant).all()
    items = session.query(MenuItem).order_by(MenuItem.created_date.desc())[0:9]
    return render_template('home.html', restaurants=restaurants, items=items)


@app.route('/restaurants/JSON/')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[r.serialize for r in restaurants])


# Create anti-forgery state token
@app.route('/login/')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/logout/')
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            # del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        return "<script>function myFunction()\
        {alert('You have successfully been logged out.');\
        window.location.href = document.referrer;}</script>\
        <body onload='myFunction()''>"
    else:
        return "<script>function myFunction() {alert('You were not logged in.'); \
        window.location.href = document.referrer;}</script>\
        <body onload='myFunction()''>"


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?\
    grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' \
    % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    # let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?\%s\
    &redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return render_template("info.html", username=login_session['username'],
                           picture=login_session['picture'])


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
        % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        # response = make_response(json.dumps('Invalid state parameter.'), 401)
        # response.headers['Content-Type'] = 'application/json'
        # return response
        return "<script>function myFunction() {alert('Invalid state parameter.'); \
        window.location.href = document.referrer;}</script>\
        <body onload='myFunction()''>"
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        # response = make_response(
        #   json.dumps('Failed to upgrade the authorization code.'), 401)
        # response.headers['Content-Type'] = 'application/json'
        # return response
        return "<script>function myFunction() \
        {alert('Failed to upgrade the authorization code.'); \
        window.location.href = document.referrer;}</script>\
        <body onload='myFunction()''>"

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

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return render_template("info.html", username=login_session['username'],
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


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
            'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Add a new restaurant
@app.route('/restaurants/newrestaurant/', methods=['GET', 'POST'])
def newRestaurant():
    if 'username' not in login_session:
        return "<script>function myFunction()\
        {alert('Please sign in/sign up to add a new restaurant.'); \
        window.location.href = '" + url_for('login') + "';}</script>\
        <body onload='myFunction()''>"
    if request.method == 'POST':

        if not validName(request.form['name']):
            return render_template('newrestaurant.html') + \
                "<script>function myFunction() \
                {alert('Invalid name. Please try again!');}</script>" + \
                "<body onload='myFunction()''>"

        newrestaurant = Restaurant(name=request.form['name'],
                                   user_id=login_session['user_id'])
        session.add(newrestaurant)
        session.commit()
        return redirect(url_for('welcome'))
    else:
        return render_template('newrestaurant.html')


# List items in a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/menuitems/')
def restaurantMenu(restaurant_id):
    try:
        restaurant_query = session.query(Restaurant)
        restaurants = restaurant_query.all()
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
        items_query = session.query(MenuItem)
        items = items_query.filter_by(restaurant_id=restaurant.id).all()
        return render_template('menu.html', restaurants=restaurants,
                               restaurant=restaurant, items=items)
    except:
        return "<script>function myFunction() {alert('Cannot find a restaurant with id "+str(restaurant_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"


@app.route('/restaurants/restaurant_<int:restaurant_id>/menuitems/JSON/')
def restaurantMenuJSON(restaurant_id):
    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
        items_query = session.query(MenuItem)
        items = items_query.filter_by(restaurant_id=restaurant.id).all()
        return jsonify(MenuItems=[i.serialize for i in items])
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a restaurant with id "+str(restaurant_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"


# Edit a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/edit/',
           methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a restaurant with id "+str(restaurant_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"

    if 'username' not in login_session:
        return "<script>function myFunction()\
        {alert('Please sign in to edit this restaurant.'); \
        window.location.href = '" + url_for('login') + "';}</script>\
        <body onload='myFunction()''>"
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction()\
        {alert('You are not authorized to edit this restaurant.'); \
        window.location.href = window.history.back();}</script>\
        <body onload='myFunction()''>"
    if request.method == 'POST':
        restaurant.name = request.form['name']

        if not validName(request.form['name']):
            template = render_template('editrestaurant.html',
                                       restaurant=restaurant)
            return "<script>function myFunction()\
            {alert('Invalid name. \Please try again!');}</script>\
            <body onload='myFunction()''>"

        session.add(restaurant)
        session.commit()
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant.id))
    else:
        return render_template('editrestaurant.html', restaurant=restaurant)


# Delete a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/delete/',
           methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a restaurant with id "+str(restaurant_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"

    if 'username' not in login_session:
        return "<script>function myFunction()\
        {alert('Please sign in to delete this restaurant.'); \
        window.location.href = '" + url_for('login') + "';}</script>\
        <body onload='myFunction()''>"
    if restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction()\
        {alert('You are not authorized to delete this restaurant.'); \
        window.location.href = window.history.back();}</script>\
        <body onload='myFunction()''>"
    if request.method == 'POST':
        items_to_delete = session.query(MenuItem)\
            .filter_by(restaurant_id=restaurant.id).all()
        for i in items_to_delete:
            session.delete(i)
            session.commit()
        session.delete(restaurant)
        session.commit()
        return redirect(url_for('welcome'))
    else:
        return render_template('deleterestaurant.html',
                               restaurant=restaurant)


# Add a new item in a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/newitem/',
           methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if 'username' not in login_session:
        return "<script>function myFunction()\
        {alert('Please sign in to add a new menu item.'); \
        window.location.href = '" + url_for('login') + "';}</script>\
        <body onload='myFunction()''>"

    try:
        restaurant_query = session.query(Restaurant)
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
        if login_session['user_id'] != restaurant.user_id:
            return "<script>function myFunction(){alert(\
            'You are not authorized to add menu items to this restaurant.'); \
            window.location.href = document.referrer;}</script>\
            <body onload='myFunction()''>"
        if request.method == 'POST':

            if not validName(request.form['name']):
                template = render_template('newmenuitem.html',
                                           restaurant_id=restaurant_id)
                return template + "<script>function myFunction() \
                {alert('Invalid name. Please try again!');}</script>\
                <body onload='myFunction()''>"

            newItem = MenuItem(name=request.form['name'],
                               description=request.form['description'],
                               price=request.form['price'],
                               course=request.form['course'],
                               restaurant_id=restaurant_id,
                               user_id=restaurant.user_id)
            session.add(newItem)
            session.commit()
            return redirect(url_for('restaurantMenu',
                                    restaurant_id=restaurant_id))
        else:
            return render_template('newmenuitem.html',
                                   restaurant_id=restaurant_id)
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a restaurant with id "+str(restaurant_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"


# Description
@app.route('/menuitems/item_<int:menu_id>/')
def menuItem(menu_id):
    try:
        item = session.query(MenuItem).filter_by(id=menu_id).one()
        return render_template('menuitem.html', item=item)
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a menu item with id "+str(menu_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"


@app.route('/menuitems/item_<int:menu_id>/JSON/')
def menuItemJSON(menu_id):
    try:
        item = session.query(MenuItem).filter_by(id=menu_id).one()
        return jsonify(Menu_Item=item.serialize)
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a menu item with id "+str(menu_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"


# Edit an item
@app.route('/menuitems/item_<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(menu_id):
    if 'username' not in login_session:
        return "<script>function myFunction()\
        {alert('Please sign in to edit this menu item.'); \
        window.location.href = '" + url_for('login') + "';}</script>\
        <body onload='myFunction()''>"
    try:
        editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a menu item with id "+str(menu_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"

    try:
        restaurant_query = session.query(Restaurant)
        restaurant_id = editedItem.restaurant_id
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a restaurant with id "+str(editedItem.restaurant_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"

    if login_session['user_id'] != restaurant.user_id:
        return "<script>function myFunction(){alert(\
        'You are not authorized to edit menu items of this restaurant.'); \
        window.location.href = window.history.back();}</script>\
        <body onload='myFunction()''>"

    if request.method == 'POST':
        if not validName(request.form['name']):
            template = render_template('editmenuitem.html',
                                       restaurant_id=editedItem.restaurant_id,
                                       menu_id=menu_id,
                                       item=editedItem)
            return template + "<script>function myFunction()\
            {alert('Invalid name. Please try again!');}</script>\
            <body onload='myFunction()''>"

        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('restaurantMenu',
                                restaurant_id=editedItem.restaurant_id))
    else:
        return render_template('editmenuitem.html',
                               restaurant_id=editedItem.restaurant_id,
                               menu_id=menu_id,
                               item=editedItem)


# Delete an item
@app.route('/menuitems/item_<int:menu_id>/delete/', methods=['GET', 'POST'])
def deleteMenuItem(menu_id):
    if 'username' not in login_session:
        return "<script>function myFunction()\
        {alert('Please sign in to delete this menu item.'); \
        window.location.href = '" + url_for('login') + "';}</script>\
        <body onload='myFunction()''>"
    try:
        itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
    except:
        return "<script>function myFunction()\
        {alert('Cannot find a menu item with id "+str(menu_id)+"'); \
        window.history.back();}</script><body onload='myFunction()''>"

    try:
        restaurant_query = session.query(Restaurant)
        restaurant_id = itemToDelete.restaurant_id
        restaurant = restaurant_query.filter_by(id=restaurant_id).one()
    except:
        return "<script>function myFunction()\
            {alert('Cannot find a restaurant with id " +\
            str(itemToDelete.restaurant_id)+"'); \
            window.history.back();}</script><body onload='myFunction()''>"

    if login_session['user_id'] != restaurant.user_id:
        return "<script>function myFunction(){alert(\
        'You are not authorized to delete \menu items of this restaurant.');\
        window.location.href = window.history.back();}</script>\
        <body onload='myFunction()''>"

    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('restaurantMenu',
                                restaurant_id=itemToDelete.restaurant_id))
    else:
        return render_template('deletemenuitem.html', item=itemToDelete)


@app.errorhandler(404)
def page_not_found(error):
    return "Page not found"


def validName(name):
    if name == '':
        return False
    return True

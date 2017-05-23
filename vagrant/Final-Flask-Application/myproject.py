from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mydatabase import Base, Restaurant, MenuItem, User
import random, httplib2, json, string
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from flask import session as login_session
import requests


app = Flask(__name__)

CLIENT_ID = json.loads(
	open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Welcome page
@app.route('/')
@app.route('/restaurants')
def welcome():
	restaurants = session.query(Restaurant).all()
	items = session.query(MenuItem).order_by(MenuItem.created_date.desc())[0:10]
	return render_template('welcome.html', restaurants = restaurants, items = items)

@app.route('/restaurants/JSON')
def restaurantsJSON():
	restaurants = session.query(Restaurant).all()
	return jsonify(restaurants=[r.serialize for r in restaurants])

@app.route('/login')
def login():
	if 'username' in login_session:
		return "<script>function myFunction() {alert('You must log out before logging into another account.'); \
		window.history.back();}</script><body onload='myFunction()''>"
	state = ''.join(random.choice(string.ascii_uppercase + string.digits)
					for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)
@app.route('/gconnect', methods=['POST'])
def gconnect():

	# Validate state token
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Obtain authorization code
	code = request.data

	try:
		# Upgrade the authorization code into a credentials object
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

	stored_access_token = login_session.get('access_token')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_access_token is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'), 200)
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

	# see if user exists, if it doesn't make a new one
	user_id = getUserID(login_session['email'])
	if not user_id:
		user_id = createUser(login_session)
	login_session['user_id'] = user_id

	output = ''
	output += '<h2>Welcome, '
	output += login_session['username']
	output += '!</h2>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 100px; height: 100px;border-radius: 50px;-webkit-border-radius: 50px;-moz-border-radius: 50px;"> '
	print "done!"
	return output

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/logout')
def gdisconnect():
	if not 'username' in login_session:
		return "<script>function myFunction() {alert('You have not logged in.'); \
		window.history.back();}</script><body onload='myFunction()''>"

	access_token = login_session['access_token']
	print 'In gdisconnect access token is %s', access_token
	print 'User name is: ' 
	print login_session['username']
	if access_token is None:
		print 'Access Token is None'
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	print 'result is '
	print result
	if result['status'] == '200':
		del login_session['access_token'] 
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']
		# response = make_response(json.dumps('Successfully disconnected.'), 200)
		# response.headers['Content-Type'] = 'application/json'
		# return response
		return "<script>function myFunction() {alert('Successfully disconnected.'); \
		window.location.href = '/';}</script><body onload='myFunction()''>"
	else:
		# response = make_response(json.dumps('Failed to revoke token for given user.', 400))
		# response.headers['Content-Type'] = 'application/json'
		# return response
		return "<script>function myFunction() {alert('Failed to revoke token for given user.'); \
		window.location.href = '/';}</script><body onload='myFunction()''>"

# User Helper Functions

def createUser(login_session):
	newUser = User(name=login_session['username'], email=login_session[
				   'email'], picture=login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email=login_session['email']).one()
	return user.id

def getUserInfo(user_id):
	user = session.query(User).filter_by(id=user_id).one()
	return user

def getUserID(email):
	try:
		user = session.query(User).filter_by(email=email).one()
		return user.id
	except:
		return None

# Add a new restaurant
@app.route('/restaurants/newrestaurant/', methods = ['GET', 'POST'])
def newRestaurant():
	if 'username' not in login_session:
		return redirect(url_for('login'))
	if request.method == 'POST':
		newrestaurant = Restaurant(name = request.form['name'], user_id=login_session['user_id'])
		session.add(newrestaurant)
		session.commit()
		return redirect(url_for('welcome'))
	else:
		return render_template('newrestaurant.html')

# List items in a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/menuitems')
def restaurantMenu(restaurant_id):
	restaurants = session.query(Restaurant).all()
	restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
	items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()
	return render_template('menu.html', restaurants = restaurants, restaurant=restaurant, items=items)

@app.route('/restaurants/restaurant_<int:restaurant_id>/menuitems/JSON')
def restaurantMenuJSON(restaurant_id):
	restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
	items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
	return jsonify(MenuItems=[i.serialize for i in items])

# Edit a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/edit/', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
	restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
	if 'username' not in login_session:
		return redirect(url_for('login'))
	if restaurant.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to edit this restaurant.'); \
		window.history.back();}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		restaurant.name = request.form['name']
		session.add(restaurant)
		session.commit()
		return redirect(url_for('restaurantMenu', restaurant_id = restaurant.id))
	else:
		return render_template('editrestaurant.html', restaurant = restaurant)

# Delete a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/delete/', methods = ['GET', 'POST'])
def deleteRestaurant(restaurant_id):
	restaurant_to_delete = session.query(Restaurant).filter_by(id = restaurant_id).one()
	if 'username' not in login_session:
		return redirect(url_for('login'))
	if restaurant_to_delete.user_id != login_session['user_id']:
		return "<script>function myFunction() {alert('You are not authorized to delete this restaurant.'); \
		window.history.back();}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		items_to_delete = session.query(MenuItem).filter_by(restaurant_id = restaurant_to_delete.id).all()
		for i in items_to_delete:
			session.delete(i)
			session.commit()
		session.delete(restaurant_to_delete)
		session.commit()
		return redirect(url_for('welcome'))
	else:
		return render_template('deleterestaurant.html', restaurant = restaurant_to_delete)

# Add a new item in a restaurant
@app.route('/restaurants/restaurant_<int:restaurant_id>/newitem/', methods = ['GET', 'POST'])
def newMenuItem(restaurant_id):
	if 'username' not in login_session:
		return redirect(url_for('login'))
	restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
	if login_session['user_id'] != restaurant.user_id:
		return "<script>function myFunction() {alert('You are not authorized to add menu items to this restaurant.'); \
		window.history.back();}</script><body onload='myFunction()''>"
	
	if request.method == 'POST':
		newItem = MenuItem(name=request.form['name'], description=request.form['description'], 
							price=request.form['price'], course=request.form['course'], 
							restaurant_id=restaurant_id, user_id=restaurant.user_id)
		session.add(newItem)
		session.commit()
		return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
	else:
		return render_template('newmenuitem.html', restaurant_id=restaurant_id)

# Description
@app.route('/menuitems/item_<int:menu_id>/')
def menuItem(menu_id):
	item = session.query(MenuItem).filter_by(id=menu_id).one()
	return render_template('menuitem.html', item=item)

@app.route('/menuitems/item_<int:menu_id>/JSON')
def menuItemJSON(menu_id):
	item = session.query(MenuItem).filter_by(id=menu_id).one()
	return jsonify(Menu_Item=item.serialize)

# Edit an item
@app.route('/menuitems/item_<int:menu_id>/edit/', methods = ['GET', 'POST'])
def editMenuItem(menu_id):
	if 'username' not in login_session:
		return redirect(url_for('login'))

	editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
	restaurant = session.query(Restaurant).filter_by(id=editedItem.restaurant_id).one()

	if login_session['user_id'] != restaurant.user_id:
		return "<script>function myFunction() {alert('You are not authorized to edit menu items of this restaurant.'); \
		window.history.back();}</script><body onload='myFunction()''>"

	if request.method == 'POST':
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
		return redirect(url_for('restaurantMenu', restaurant_id=editedItem.restaurant_id))
	else:
		return render_template(
			'editmenuitem.html', restaurant_id=editedItem.restaurant_id, menu_id=menu_id, item=editedItem)

# Delete an item
@app.route('/menuitems/item_<int:menu_id>/delete/', methods = ['GET', 'POST'])
def deleteMenuItem(menu_id):
	if 'username' not in login_session:
		return redirect(url_for('login'))

	itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
	restaurant = session.query(Restaurant).filter_by(id=itemToDelete.restaurant_id).one()

	if login_session['user_id'] != restaurant.user_id:
		return "<script>function myFunction() {alert('You are not authorized to delete menu items of this restaurant.'); \
		window.history.back();}</script><body onload='myFunction()''>"

	if request.method == 'POST':
		session.delete(itemToDelete)
		session.commit()
		return redirect(url_for('restaurantMenu', restaurant_id=itemToDelete.restaurant_id))
	else:
		return render_template('deletemenuitem.html', item=itemToDelete)

if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=8080)

from myapp.controllers import *


# ==========================CRUD==========================
@app.route('/api/v1/users', methods=['POST'])
def create_user():
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400
    errors = validate_insertion(request.json, ['email', 'password'])

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    name = request.json.get('name')
    email = request.json.get('email')
    picture = request.json.get('picture')
    password = request.json.get('password')

    if session.query(User).filter_by(email=email).first() is not None:
        return jsonify({'message': 'user already existed'}), 409

    user = User(name=name, email=email, picture=picture)
    user.password = user.hash_password(password)
    session.add(user)
    session.commit()

    user.token = user.generate_auth_token(6000)
    session.add(user)
    session.commit()
    return jsonify({'token': user.token}), 201


@app.route('/api/v1/users', methods=['GET'])
def get_users():
    users = session.query(User).all()
    return jsonify(users=[u.serialize for u in users])


@app.route('/api/v1/users', methods=['PUT'])
@login_required
def update_user():
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400
    errors = validate_update(request.json, ['email', 'password'])

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    user = session.query(User).filter_by(id=g.user.id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'name' in request.json:
        user.name = request.json.get('name')
    if 'email' in request.json:
        user.email = request.json.get('email')
    if 'picture' in request.json:
        user.picture = request.json.get('picture')
    if 'password' in request.json:
        user.password = request.json.get('password')

    session.add(user)
    session.commit()
    return jsonify(user.serialize), 200


@app.route('/api/v1/users', methods=['DELETE'])
@login_required
def delete_user():
    user = session.query(User).filter_by(id=g.user.id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    session.delete(user)
    session.commit()
    return jsonify(users=[u.serialize for u in users]), 200

# ================================================================


# Log in with token or username/password or OAuth
@app.route('/api/v1/login', methods=['POST'])
def login():
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    # Login with token
    if request.headers and 'token' in request.headers:
        token = request.headers.get('token')
        user_id = User.verify_auth_token(token)
        if user_id:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                return jsonify({'token': token}), 200
        return jsonify({'error': 'invalid token'}), 200

    # Login with OAuth
    if 'provider' in request.json:
        provider = request.json.get('provider')
        code = request.json.get('code')
        if provider == 'google' and code:
            return gconnect(code)
        elif provider == 'facebook' and code:
            return fbconnect(code)
        else:
            return jsonify({'error': 'invalid provider'}), 200

    # Login with email and password
    if 'email' not in request.json:
        return jsonify({'error': 'missing email'}), 400

    if 'password' not in request.json:
        return jsonify({'error': 'missing password'}), 400

    password = request.json.get('password')
    email = request.json.get('email')
    user = session.query(User).filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Invalid email"}), 404

    if not user.verify_password(password):
        return jsonify({"error": "Invalid password"}), 400

    token = user.generate_auth_token(6000)
    user.token = token
    session.add(user)
    session.commit()

    return jsonify({'token': token}), 200


@app.route('/api/v1/logout', methods=['POST'])
@login_required
def logout():
    if g.user.gplus_access_token is not None:
        response = gdisconnect(g.user.gplus_access_token)
        if response:
            return response

    if g.user.fb_access_token is not None:
        fbdisconnect(g.user.fb_id, g.user.fb_access_token)

    g.user.logout()
    session.add(g.user)
    session.commit()

    return jsonify({'result': True}), 200


def gconnect(code):
    # Use one-time code to get credentials
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        return jsonify({'error': 'Failed to upgrade the authorization code.'}), 401

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        return jsonify({'error': result.get('error')}), 500

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        return jsonify({'error': "Token's user ID doesn't match given user ID."}), 401

    # Verify that the access token is valid for this app.
    if result['issued_to'] != json.loads(
            open('client_secrets.json', 'r').read())['web']['client_id']:
        return jsonify({'error': "Token's client ID does not match app's."}), 401

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()

    # see if user exists. If it doesn't, make a new one
    user = session.query(User).filter_by(email=data["email"]).first()
    if not user:
        user = User(
            name=data['name'],
            picture=data['picture'],
            email=data['email'])
        session.add(user)
        session.commit()

    user.gplus_access_token = credentials.access_token
    user.gplus_id = gplus_id
    user.token = user.generate_auth_token(600)

    session.add(user)
    session.commit()

    return jsonify({'token': user.token}), 200


def gdisconnect(access_token):
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        return False
    return True


def fbconnect(code):
    # print "access token received %s " % access_token

    # Get access token from one-time exchange code
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=' \
          'fb_exchange_token&client_id=%s&client_secret=%s'\
          '&fb_exchange_token=%s' % (app_id, app_secret, code)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    access_token = json.loads(result)['access_token']

    url = "https://graph.facebook.com/v2.9/me?"\
          "fields=email,name,id,picture&access_token=%s" % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    # see if user exists. If it doesn't, make a new one
    user = session.query(User).filter_by(email=data["email"]).first()
    if not user:
        user = User(
            name=data['name'],
            picture=data["picture"]["data"]["url"],
            email=data['email'])
        session.add(user)
        session.commit()

    user.fb_access_token = access_token
    user.fb_id = data["id"]
    user.token = user.generate_auth_token(600)

    session.add(user)
    session.commit()

    return jsonify({'token': user.token}), 200


def fbdisconnect(facebook_id, access_token):
    # The access token must me included to successfully logout
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
        % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    if result.get('error'):
        return False
    return True

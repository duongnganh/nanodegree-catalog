from myapp.controllers import *


# ==========================CRUD==========================
@app.route('/api/v1/users', methods=['POST'])
def create_user():
    if not request.json:
        abort(400, 'Invalid json')
    errors = validate_insertion(request.json, ['email', 'password'])

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    name = request.json.get('name')
    email = request.json.get('email')
    picture = request.json.get('picture')
    password = request.json.get('password')

    if session.query(User).filter_by(email=email).first() is not None:
        abort(409, 'User already existed')


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
        abort(400, 'Invalid json')
    errors = validate_update(request.json, ['password'])

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    user = session.query(User).filter_by(id=g.user.id).first()
    if not user:
        abort(404, 'User not found')

    if 'email' in request.json:
        abort(400, 'Cannot change email')

    if 'name' in request.json:
        user.name = request.json.get('name')
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
        abort(404, 'User not found')

    session.delete(user)
    session.commit()
    return jsonify(users=[u.serialize for u in users]), 200

# ================================================================


# Log in with token or username/password or OAuth
@app.route('/api/v1/login', methods=['POST'])
def login():
    if not request.json:
        abort(400, 'Invalid json')

    # Login with token
    if request.headers and 'Authorization' in request.headers:
        token = request.headers.get('Authorization')
        user_id = User.verify_auth_token(token)
        if user_id:
            user = session.query(User).filter_by(id=user_id).first()
            if user and user.token:
                return jsonify({'token': token}), 200
        abort(400, 'Invalid token')

    # Login with OAuth
    if 'provider' in request.json:
        provider = request.json.get('provider')
        code = request.json.get('code')
        if provider == 'google' and code:
            return gconnect(code)
        elif provider == 'facebook' and code:
            return fbconnect(code)
        else:
            abort(400, 'Invalid provider')

    # Login with email and password
    if 'email' not in request.json:
        abort(400, 'Missing email')

    if 'password' not in request.json:
        abort(400, 'Missing password')

    password = request.json.get('password')
    email = request.json.get('email')
    user = session.query(User).filter_by(email=email).first()

    if not user:
        abort(404, 'Invalid email')

    if not user.verify_password(password):
        abort(403, 'Invalid password')

    token = user.generate_auth_token(6000)
    user.token = token
    session.add(user)
    session.commit()

    return jsonify({'token': token}), 200


@app.route('/api/v1/logout', methods=['GET'])
@login_required
def logout():
    errors = []
    if g.user.gplus_access_token is not None:
        if not gdisconnect():
            error = dict({'error': 'Cannot disconnect from Google Plus'})
            errors.append(error)

    if g.user.fb_access_token is not None:
        if not fbdisconnect():
            error = dict({'error': 'Cannot disconnect from Facebook'})
            errors.append(error)

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

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
        abort(401, 'Failed to upgrade the authorization code')

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if 'error' in result:
        abort(500, result['error'])

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        abort(401, "Token's user ID doesn't match given user ID.")

    # Verify that the access token is valid for this app.
    if result['issued_to'] != json.loads(
            open('client_secrets.json', 'r').read())['web']['client_id']:
        abort(401, "Token's client ID does not match app's.")

    # Access token is verified and valid. Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()

    # See if user exists. If it doesn't, make a new one
    user = session.query(User).filter_by(email=data['email']).first()
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


def gdisconnect():
    access_token = g.user.gplus_access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        return False
    return True


def fbconnect(code):
    # Get access token from one-time exchange code
    # Verify that the access token is valid for this user and app
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=' \
          'fb_exchange_token&client_id=%s&client_secret=%s'\
          '&fb_exchange_token=%s' % (app_id, app_secret, code)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if 'error' in result:
        abort(401, result['error']['message'])

    # Check that the access token is valid.
    access_token = result['access_token']
    url = ('https://graph.facebook.com/me?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if 'error' in result:
        abort(500, result['error']['message'])

    # Access token is verified and valid. Get user info
    url = 'https://graph.facebook.com/v2.9/me?'\
          'fields=email,name,id,picture&access_token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    # see if user exists. If it doesn't, make a new one
    user = session.query(User).filter_by(email=data['email']).first()
    if not user:
        user = User(
            name=data['name'],
            picture=data['picture']['data']['url'],
            email=data['email'])
        session.add(user)
        session.commit()

    user.fb_access_token = access_token
    user.fb_id = data['id']
    user.token = user.generate_auth_token(600)

    session.add(user)
    session.commit()

    return jsonify({'token': user.token}), 200


def fbdisconnect():
    facebook_id = g.user.fb_id
    access_token = g.user.fb_access_token
    # The access token must me included to successfully logout
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
        % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    data = json.loads(result)
    if 'error' in data:
        return False
    return True

from myapp.controllers import *


# Log in with token or username/password or OAuth
@app.route('/api/v1/login', methods=['GET', 'POST'])
def api_login():
    token = request.cookies.get('token')
    if token:
        print(token)
        user_id = User.verify_auth_token(token)
        if user_id:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                g.user = user
                return jsonify({'result': True}), 200

    if request.method == 'GET':
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        return render_template('login.html', STATE=state)
    else:
        if not request.json:
            return jsonify({'error': 'invalid json'}), 400
        errors = User.validate(request.json)

        if len(errors) != 0:
            return jsonify(errors=[error for error in errors]), 400

        name = request.json.get('name')
        password = request.json.get('password')
        email = request.json.get('email')
        picture = request.json.get('picture')
        user = session.query(User).filter_by(name=name, email=email, picture=picture).first()

        if not user:
            return jsonify({"error": "Invalid name"}), 404

        if not user.verify_password(password):
            return jsonify({"error": "Invalid password"}), 400

        g.user = user

        token = user.generate_auth_token(6000)
        response = make_response(jsonify({'result': True}), 200)
        response.set_cookie('token', token)

        return response

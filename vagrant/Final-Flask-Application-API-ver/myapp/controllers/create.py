from myapp.controllers import *


@app.route('/api/v1/users', methods=['POST'])
def create_user():
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400
    errors = User.validate(request.json)

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    name = request.json.get('name')
    password = request.json.get('password')

    if session.query(User).filter_by(name=name).first() is not None:
        return jsonify({'message': 'user already existed'}), 409

    user = User(name=name)
    user.hash_password(password)
    session.add(user)
    session.commit()

    token = user.generate_auth_token()
    response = make_response(jsonify({'result': True}), 201)
    response.set_cookie('token', token)
    api_login()
    return response


@app.route('/api/v1/restaurants', methods=['POST'])
@login_required
def create_restaurant():
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400
    errors = Restaurant.validate(request.json)

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    restaurant = Restaurant(name=request.json.get('name'),
                            user_id=g.user.id)
    session.add(restaurant)
    session.commit()
    return jsonify(result=True), 201


@app.route('/api/v1/restaurants/<int:restaurant_id>/menuitems',
           methods=['POST'])
@login_required
def create_menuitem(restaurant_id):
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400
    errors = MenuItem.validate(request.json)

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
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

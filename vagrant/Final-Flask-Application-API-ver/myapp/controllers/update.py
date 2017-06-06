from myapp.controllers import *


@app.route('/api/v1/users', methods=['PUT'])
@login_required
def update_user():
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    user = session.query(User).filter_by(id=g.user.id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'name' in request.json:
        user.name = request.json.get('name')
    if 'password' in request.json:
        user.password = request.json.get('password')

    session.add(user)
    session.commit()

    return jsonify(result=True), 200


@app.route('/api/v1/restaurants/<int:restaurant_id>', methods=['PUT'])
@login_required
def update_restaurant(restaurant_id):
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    restaurant.name = request.json.get('name')

    session.add(restaurant)
    session.commit()
    return jsonify(result=True), 200


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['PUT'])
@login_required
def update_menuitem(menu_id):
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    item = session.query(MenuItem).filter_by(id=menu_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    restaurant = session.query(Restaurant).filter_by(
        id=item.restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    if 'name' in request.json:
        item.name = request.json.get('name')
    if 'description' in request.json:
        item.description = request.json.get('description')
    if 'price' in request.json:
        item.price = request.json.get('price')
    if 'course' in request.json:
        item.course = request.json.get('course')

    session.add(item)
    session.commit()
    return jsonify(result=True), 200

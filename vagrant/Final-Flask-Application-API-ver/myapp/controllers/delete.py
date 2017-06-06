from myapp.controllers import *


@app.route('/api/v1/users', methods=['DELETE'])
@login_required
def delete_user():

    user = session.query(User).filter_by(id=g.user.id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    session.delete(user)
    session.commit()

    api_logout()

    return jsonify(result=True), 200


@app.route('/api/v1/restaurants/<int:restaurant_id>', methods=['DELETE'])
@login_required
def delete_restaurant(restaurant_id):
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    for i in items:
        session.delete(i)
        session.commit()

    session.delete(restaurant)
    session.commit()
    return jsonify(result=True), 200


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['DELETE'])
@login_required
def delete_menuitem(menu_id):
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    item = session.query(MenuItem).filter_by(id=menu_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    restaurant = session.query(Restaurant).filter_by(
        id=item.restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    session.delete(item)
    session.commit()

    return jsonify(result=True), 200

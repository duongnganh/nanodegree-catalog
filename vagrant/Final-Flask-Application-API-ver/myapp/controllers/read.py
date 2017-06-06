from myapp.controllers import *


@app.route('/api/v1/users', methods=['GET'])
def get_users():
    users = session.query(User).all()
    return jsonify(users=[u.serialize for u in users])


@app.route('/api/v1/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[r.serialize for r in restaurants])


@app.route('/api/v1/restaurants/<int:restaurant_id>/menuitems',
           methods=['GET'])
def get_menuitems(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    items_query = session.query(MenuItem)
    items = items_query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['GET'])
def get_menuitem(menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(item=item.serialize)

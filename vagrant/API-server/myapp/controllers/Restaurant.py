from myapp.controllers import *


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


@app.route('/api/v1/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[r.serialize for r in restaurants])


@app.route('/api/v1/restaurants/<int:restaurant_id>', methods=['PUT'])
@login_required
def update_restaurant(restaurant_id):
    if not request.json:
        return jsonify({'error': 'invalid json'}), 400

    if request.json.get('delete') == 'true':
        return delete_restaurant(restaurant_id)

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        return jsonify({'error': 'Restaurant not found'}), 404

    if restaurant.user_id != g.user.id:
        abort(403)

    restaurant.name = request.json.get('name')

    session.add(restaurant)
    session.commit()
    return jsonify(result=True), 200


def delete_restaurant(restaurant_id):
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

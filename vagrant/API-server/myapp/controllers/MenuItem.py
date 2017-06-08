from myapp.controllers import *


@app.route('/api/v1/restaurants/<int:restaurant_id>/menuitems',
           methods=['POST'])
@login_required
def create_menuitem(restaurant_id):
    if not request.json:
        abort(400, 'Invalid json')
    errors = validate_insertion(request.json, ['name', 'description', 'price', 'course'])

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        abort(404, 'Restaurant not found')

    if restaurant.user_id != g.user.id:
        abort(403, 'You are not the owner of this restaurant')

    item = MenuItem(name=request.json.get('name'),
                    description=request.json.get('description'),
                    price=request.json.get('price'),
                    course=request.json.get('course'),
                    restaurant_id=restaurant_id,
                    user_id=restaurant.user_id)

    session.add(item)
    session.commit()
    return jsonify(item=item.serialize), 201


@app.route('/api/v1/restaurants/<int:restaurant_id>/menuitems',
           methods=['GET'])
def get_menuitems(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if not restaurant:
        abort(404, 'Restaurant not found')

    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    return jsonify(items=[i.serialize for i in items]), 200


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['GET'])
def get_menuitem(menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).first()
    if not item:
        abort(404, 'Item not found')
    return jsonify(item=item.serialize), 200


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['PUT'])
@login_required
def update_menuitem(menu_id):
    if not request.json:
        abort(400, 'Invalid json')
    errors = validate_update(request.json, ['name', 'description', 'price', 'course'])

    if len(errors) != 0:
        return jsonify(errors=[error for error in errors]), 400

    item = session.query(MenuItem).filter_by(id=menu_id).first()
    if not item:
        abort(404, 'Item not found')

    restaurant = session.query(Restaurant).filter_by(
        id=item.restaurant_id).first()
    if not restaurant:
        abort(404, 'Restaurant not found')

    if restaurant.user_id != g.user.id:
        abort(403, 'You are not the owner of this restaurant')

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
    return jsonify(item.serialize), 200


@app.route('/api/v1/menuitems/<int:menu_id>', methods=['DELETE'])
@login_required
def delete_menuitem(menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).first()
    if not item:
        abort(404, 'Item not found')

    restaurant = session.query(Restaurant).filter_by(
        id=item.restaurant_id).first()
    if not restaurant:
        abort(404, 'Restaurant not found')

    if restaurant.user_id != g.user.id:
        abort(403, 'You are not the owner of this restaurant')

    session.delete(item)
    session.commit()
    return jsonify(items=[i.serialize for i in items]), 200

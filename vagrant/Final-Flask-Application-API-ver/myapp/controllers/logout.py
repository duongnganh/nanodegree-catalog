from myapp.controllers import *
from myapp.controllers.google import gdisconnect
from myapp.controllers.facebook import fbdisconnect


@app.route('/api/v1/logout')
@login_required
def api_logout():
    g.user = None
    if login_session.get('provider') == 'google':
        gdisconnect()
    elif login_session.get('provider') == 'facebook':
    	fbdisconnect()
    login_session.clear()
    response = make_response(jsonify({'result': True}), 200)
    response.set_cookie('token', '', expires=0)

    return response

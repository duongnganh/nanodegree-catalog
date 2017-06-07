from flask import Flask, render_template

app = Flask(__name__)


# Log in with token or username/password or OAuth
@app.route('/oauth')
def login():
    return render_template('login.html')


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.run(host='0.0.0.0', port=5000)


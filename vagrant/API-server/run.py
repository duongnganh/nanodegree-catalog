from myapp.controllers import app
from initialize_db import delete, add
import sys

if __name__ == '__main__':
    args = sys.argv[1:]
    run = True
    for a in args:
        if a == "-h":
            print("Options:")
            print("-r : reset current database")
            print("-d : turn on debug")
            print("-h : help")
            run = False
        else:
            if a == "-r":
                delete()
                add()
            if a == "-d":
                app.debug = True
    if run:
        app.secret_key = 'super_secret_key'
        app.run(host='0.0.0.0', port=8080)

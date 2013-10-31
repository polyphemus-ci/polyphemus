import json
import pprint
from functools import wraps

from flask import Flask, request

from .event import Event

app = Flask('polyphemus')

def exec_plugins(f):
    """Decorator for executing plugin pipeline.  This should normally be
    the bottom-most decorator to ensure that the plugins are executed after 
    all other steps, but before the application routing.  Most plugins will 
    expect an event to be added to the file.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        rtn = f(*args, **kwargs)
        app.plugins.execute()
        return rtn
    return wrapper

@app.route('/github', methods=['GET', 'POST'])
@exec_plugins
def github():
    print request.method
    payload = json.loads(request.form['payload'])
    app.plugins.rc.event = Event(name='github', data=payload)
    return request.method + ": github"

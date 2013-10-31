import json
import pprint
from functools import wraps

from flask import Flask, request

from .event import Event

app = Flask('polyphemus')

def exec_plugins(f):
    """Decorator for executing plugin pipeline.  This should normally be
    the top-most decorator to ensure that the plugins are executed after 
    all other steps.  Most plugins will expect an event to be added to 
    the file.
    """
    @wraps
    def wrapper(*args, **kwargs):
        rtn = f(*args, **kwargs)
        app.plugins.execute()
        return rtn
    return wrapper

@exec_plugins
@app.route('/github', methods=['GET', 'POST'])
def root():
    print request.method
    payload = json.loads(request.form['payload'])
    rc.event = Event(name='github', data=payload)

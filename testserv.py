import pprint
import json

from flask import Flask
from flask import request
app = Flask('polyphemus')

@app.route('/', methods=['GET', 'POST'])
def root():
    print request.method
    #print dir(request)
    payload = json.loads(request.form['payload'])
    pprint.pprint(payload)

if __name__ == '__main__':
#    app.debug = True
    app.run(host='0.0.0.0')

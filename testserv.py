from flask import Flask
app = Flask('polyphemus')

@app.route('/', methods=['GET', 'POST'])
def root():
    print request.method
    print dir(request)

if __name__ == '__main__':
    app.debug = True
    app.run()

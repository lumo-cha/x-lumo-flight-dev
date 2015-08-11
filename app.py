import os
import flask
import json

app = flask.Flask(__name__)

@app.before_request
def preprocess():
    pass


@app.after_request
def postprocess(response):
    pass


@app.errorhandler(404)
def pageNotFoundError(error):
    error_json = {"error" : "HTTP Page Not Found", "error_code" : 404}
    return json.dumps(error_json)


@app.errorhandler(405)
def invalidMethod(error):
    error_json = {"error": "HTTP Method Not Allowed", "error_code": 405}
    return json.dumps(error_json)


@app.errorhandler(413)
def contentLimitExceeded(error):
    error_json = {"error" : "HTTP Content Length Exceeded" , "error_code" : 413}
    return json.dumps(error_json)


@app.route('/')
def hello():
    return 'Hello World!'



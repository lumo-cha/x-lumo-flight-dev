import os
import json
import gzip
from flask import *
from functools import wraps
from werkzeug.exceptions import BadRequest
from cStringIO import StringIO

# configure the app
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = True
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 2024  # bytes

@app.before_request
def preprocess():
    pass

@app.after_request
def postprocess(response):
    return response

# --------------------------------------------------------------------------------------------------
#   function decorators
def validate_json(f):
    """ add this decorator to endpoints that are designed for proper json payloads """
    @wraps(f)
    def validate(*args, **kw):
        try:
            json_data = request.get_json()
            if not json_data:
                return jsonify({"error": "improper content-type. must be application/json"}), 400
        except BadRequest as e:
            return jsonify({"error": "improper json"}), 400
        return f(*args, **kw)
    return validate


def gzipped_response(f):
    """ determine if we should gzip the response of an endpoint """
    @wraps(f)
    def gzipper(*args, **kwargs):
        @after_this_request
        def zipper(response):
            gzip_ok = request.headers.get('Accept-Encoding', '')
            pre_compress = len(response.data)

            # dont gzip if the requestor doesnt want it or if the data is small already
            if 'gzip' not in gzip_ok.lower() or len(response.data) <= 1024: return response

            # don't do anything with bad responses or responses that already have a content-encoding
            if (response.status_code < 200 or response.status_code >= 300 or\
                'Content-Encoding' in response.headers):
                return response

            # gzip the response
            gzip_buffer = StringIO()
            gzip_file = gzip.GzipFile(mode='wb', fileobj=gzip_buffer)
            gzip_file.write(response.data)
            gzip_file.close()

            # put together the response (headers + content). we add a custom header key containing
            # the pre-compression data size.
            response.direct_passthrough = False
            response.data = gzip_buffer.getvalue()
            response.headers["original_bytes"] = pre_compress
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'
            response.headers['Content-Length'] = len(response.data)
            return response
        return f(*args, **kwargs)
    return gzipper



@app.route('/uptest', methods=["GET", "POST"])
def uptest():
    return 'Hello World'


@app.route("/json_echo", methods=["POST"])
@validate_json      # ensure proper JSON is sent in the request
@gzipped_response   # apply content-encoding:gzip to the response if necessary
def json_test():
    try:
        json_data = request.get_json()
        return jsonify(json_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------------------------------
#   Error Response Handling
@app.errorhandler(404)
def pageNotFoundError(error):
    error_json = {"error" : "HTTP Page Not Found", "error_code" : 404}
    return jsonify(error_json), 404

@app.errorhandler(405)
def invalidMethod(error):
    error_json = {"error": "HTTP Method Not Allowed", "error_code": 405}
    return jsonify(error_json), 405

@app.errorhandler(413)
def contentLimitExceeded(error):
    error_json = {"error" : "HTTP Content Length Exceeded" , "error_code" : 413}
    return jsonify(error_json), 413


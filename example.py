import requests
import json
import pprint

pp = pprint.PrettyPrinter(indent=4, width=100)

# first get some json
response = requests.get(url="https://flight-dashboard.herokuapp.com/api/generaterun/cha@lumobodytech.com")
json_str = json.dumps(response.json())

# now put together the request expected by /json_echo
headers = {
        # Heroku doesn't support requests with this header. their routing servers (cowboy) will
        # reject the request. Cowboy is a routing server written in erlang
        # https://news.ycombinator.com/item?id=8515856
        # "Transfer-Encoding": "gzip",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Cache-Control": "no-cache"
        }
pp.pprint("------- REQUEST HEADERS")
for k,v in headers.iteritems():
    print "\t%s -> %s" % (k, v)
pp.pprint("------- REQUEST CONTENT (first 100 chars)")
pp.pprint(json_str[:100])

response = requests.post("http://x-lumo-flight.herokuapp.com/json_echo"
        , data=json_str
        , headers=headers)

print "\n\n"

pp.pprint("------- RESPONSE HEADERS")
for k,v in response.headers.iteritems():
    print "\t%s -> %s" % (k, v)
pp.pprint("------- RESPONSE CONTENT (first 100 chars)")
pp.pprint(json.dumps(response.json())[:100])


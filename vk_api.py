import urllib2
import json
from urllib import urlencode

def call_api(method, params, token):
	if isinstance(params, list):
		params_list = [kv for kv in params]
	elif isinstance(params, dict):
		params_list = params.items()
	else:
		params_list = [params]
	params_list.append(("access_token", token))
	url = "https://api.vk.com/method/%s?%s" % (method, urlencode(params_list)) 
	return json.loads(urllib2.urlopen(url).read())["response"]
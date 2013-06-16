import urllib2
import json
import time
from urllib import urlencode

last_time = 0.0

def call_api(method, params, token):
	global last_time

	# Make timeout between api requests retries
	time.sleep(max(0.0, 0.3333 - (time.clock() - last_time)))

	if isinstance(params, list):
		params_list = params[:]
	elif isinstance(params, dict):
		params_list = params.items()
	else:
		params_list = [params]

	params_list += [('access_token', token)]
	url = 'https://api.vk.com/method/%s?%s' % (method, urlencode(params_list))

	response = urllib2.urlopen(url).read()
	last_time = time.clock()

	return json.loads(response)['response']

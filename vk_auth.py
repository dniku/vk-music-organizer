import cookielib
import urllib2
import urllib
from urlparse import urlparse
from HTMLParser import HTMLParser

class FormParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)

		self.url = None
		self.params = {}
		self.in_form = False
		self.form_parsed = False
		self.method = 'GET'

	def handle_starttag(self, tag, attrs):
		tag = tag.lower()

		if tag == 'form':
			if self.form_parsed:
				raise RuntimeError('Two <form>s on the page.')

			if self.in_form:
				raise RuntimeError('Nested <form>s.')

			self.in_form = True

		if not self.in_form:
			return

		attrs = dict((name.lower(), value) for name, value in attrs)

		if tag == 'form':
			self.url = attrs['action']

			if 'method' in attrs:
				self.method = attrs['method']
		elif tag == 'input' and attrs.viewkeys() >= {'type', 'name'} and \
			attrs['type'] in ['hidden', 'text', 'password']:
			self.params[attrs['name']] = attrs['value'] if 'value' in attrs else ''

	def handle_endtag(self, tag):
		tag = tag.lower()

		if tag == 'form':
			if not self.in_form:
				raise RuntimeError('Unexpected end of <form>.')

			self.in_form = False
			self.form_parsed = True

def auth_user(email, password, client_id, scope, opener):
	response = opener.open(
		"http://oauth.vk.com/oauth/authorize?" + \
		"redirect_uri=http://oauth.vk.com/blank.html&response_type=token&" + \
		"client_id=%s&scope=%s&display=wap" % (client_id, ",".join(scope))
		)
	doc = response.read()

	parser = FormParser()
	parser.feed(doc)
	parser.close()

	params = parser.params

	if not parser.form_parsed or parser.url is None:
		raise RuntimeError('Form wasn\'t parsed properly.')

	if not params.viewkeys() >= {'pass', 'email'}:
		print 'params: %s' % params
		# raise RuntimeError('Some essential data is missing in the form.')
		exit()

	params.update({'email': email, 'pass': password})

	if parser.method.lower() == 'post':
		response = opener.open(parser.url, urllib.urlencode(params))
	else:
		raise NotImplementedError("Method '%s' is not supported" % parser.method)

	return response.read(), response.geturl()

def give_access(doc, opener):
	parser = FormParser()
	parser.feed(doc)
	parser.close()

	if not parser.form_parsed or parser.url is None:
		  raise RuntimeError('Form wasn\'t parsed properly.')

	if parser.method.lower() == 'post':
		response = opener.open(parser.url, urllib.urlencode(parser.params))
	else:
		raise NotImplementedError("Method '%s' is not supported" % parser.method)

	return response.geturl()


def auth(email, password, client_id, scope):
	# Ensuring that scope is a list
	if not isinstance(scope, list):
		scope = [scope]

	opener = urllib2.build_opener(
		urllib2.HTTPCookieProcessor(cookielib.CookieJar()),
		urllib2.HTTPRedirectHandler())

	# Entering login data
	doc, url = auth_user(email, password, client_id, scope, opener)

	if urlparse(url).path != '/blank.html':
		# Need to give access to requested scope
		url = give_access(doc, opener)

	if urlparse(url).path != '/blank.html':
		raise RuntimeError('Error occured while accessing the requested scope.')

	def split_key_value(kv_pair):
		kv = kv_pair.split('=')
		return kv[0], kv[1]

	answer = dict(split_key_value(kv_pair) for kv_pair in urlparse(url).fragment.split('&'))

	if not answer.viewkeys() >= {'access_token', 'user_id'}:
		raise RuntimeError('Authorization failure: did not obtain complete data.')

	return answer['access_token'], answer['user_id']

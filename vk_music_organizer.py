import os
import json
import vk_auth, vk_api
from collections import defaultdict

email = 'email@example.com'
password = 'your_password'

debug_mode = False
audios_cache = 'audios.json'
albums_cache = 'albums.json'
audios_dump = 'audios.txt'
result_dump = 'result.txt'

import pprint as module_pprint
class MyPrettyPrinter(module_pprint.PrettyPrinter):
	def format(self, object, context, maxlevels, level):
		if isinstance(object, unicode):
			return ("u'%s'" % object.encode('utf-8'), True, False)
		return module_pprint.PrettyPrinter.format(self, object, context, maxlevels, level)
pprint = MyPrettyPrinter().pprint


def load_json(filename):
	with open(filename, 'r') as f:
		return json.load(f)

def save_json(filename, obj):
	with open(filename, 'w') as f:
		json.dump(obj, f, sort_keys=True, indent=4)


class VKApi(object):
	def __init__(self, email, password, client_id, scope):
		self.email = email
		self.password = password
		self.client_id = client_id
		self.scope = scope

		self.token = None
		self.user_id = None

	def ensure_login(self):
		if self.token is None or self.user_id is None:
			self.token, self.user_id = vk_auth.auth(
				self.email, self.password, client_id=self.client_id, scope=self.scope)

	def get_audios(self, user_id=None):
		if debug_mode and os.path.exists(audios_cache):
			return load_json(audios_cache)

		self.ensure_login()

		params = {'oid': (self.user_id if user_id is None else user_id)}
		audios = vk_api.call_api('audio.get', params, self.token)[1:]  # The first item is the length

		if debug_mode:
			save_json(audios_cache, audios)

		return audios

	def get_albums(self, owner_id=None):
		if debug_mode and os.path.exists(albums_cache):
			return load_json(albums_cache)

		self.ensure_login()

		params = {'owner_id': (self.user_id if owner_id is None else owner_id), 'count': '100'}
		albums = vk_api.call_api('audio.getAlbums', params, self.token)[1:]  # The first item is the length

		if debug_mode:
			save_json(albums_cache, albums)

		return albums

	def reorder_audio(self, audio_id, owner_id=None, before=None, after=None):
		if not before and not after:
			raise ValueError('Neither before nor after were specified')

		self.ensure_login()

		params = {'aid': audio_id, 'oid': (self.user_id if owner_id is None else owner_id)}
		if before:
			params['before'] = before
		if after:
			params['after'] = after
			
		if debug_mode:
			before_piece = ' before track #%s' % before if before else ''
			after_piece  = ' after track #%s'  % after  if after  else ''
			print 'Inserting track #%s%s%s' % (audio_id, before_piece, after_piece)

		result = vk_api.call_api('audio.reorder', params, self.token)
		if result != 1:
			raise RuntimeError('API did not return success code')

class Cluster(object):
	def __init__(self, title, contents):
		self.title = title
		self.contents = contents

	def __repr__(self):
		return (u"'%s' (%d)" % (self.title, len(self.contents))).encode('utf-8')

def preprocess(audios):
	for audio in audios:
		audio['artist'] = audio['artist'].strip()
		audio['title'] = audio['title'].strip()

def split_albums(audios, album_names):
	if not audios:
		return []

	albums = defaultdict(list)
	albumfree = []
	for audio in audios:
		if 'album' in audio:
			albums[audio['album']].append(audio)
		else:
			albumfree.append(audio)
	albums = albums.values()
	albums.sort(key=lambda album: album_names[album[0]['album']])

	result = [albumfree]
	result.extend(albums)

	return result

def clusterize(audios):
	if not audios:
		return []

	clusters = []
	last_cluster = [audios[0]]

	for audio in audios[1:]:
		if audio['artist'].lower() == last_cluster[0]['artist'].lower():
			last_cluster.append(audio)
		else:
			clusters.append(Cluster(last_cluster[0]['artist'], last_cluster))
			last_cluster = [audio]
	clusters.append(Cluster(last_cluster[0]['artist'], last_cluster))

	return clusters

def merge_clusters(clusters):
	biggest_cluster_size = defaultdict(lambda: 0)
	biggest_cluster_index = {}
	for i, cluster in enumerate(clusters):
		if len(cluster.contents) > biggest_cluster_size[cluster.title]:
			biggest_cluster_size[cluster.title] = len(cluster.contents)
			biggest_cluster_index[cluster.title] = i
	result = {}
	for i, cluster in enumerate(clusters):
		biggest_index = biggest_cluster_index[cluster.title]
		if biggest_index in result:
			result[biggest_index].contents.extend(cluster.contents)
		else:
			result[biggest_index] = cluster
	result = sorted(result.items(), key=lambda (index, cluster): index)
	result = [cluster for index, cluster in result]
	return result

def flatten(alist):
	result = []
	for sublist in alist:
		result.extend(sublist)
	return result

def sort_audios(audios, album_names):
	albums = split_albums(audios, album_names)

	result = []
	for album in albums:
		album = clusterize(album)
		album = merge_clusters(album)
		album = flatten(cluster.contents for cluster in album)
		result.append(album)

	result = flatten(result)
	return result

def save_audios(audios, filename):
	def audio_to_string(audio):
		return u'\n'.join(unicode(audio[key]) for key in ('aid', 'artist', 'title'))

	audios_string = u'\n\n'.join(audio_to_string(audio) for audio in audios).encode('utf-8')

	with open(filename, 'w') as f:
		f.write(audios_string)

def main(email, password):
	vk = VKApi(
		email=email,
		password=password,
		client_id='3710018',
		scope=['audio']
		)

	audios = vk.get_audios()
	preprocess(audios)
	if debug_mode:
		save_audios(audios, audios_dump)

	# Restructuring from the list to a dictionary for quick lookup
	album_names = {unicode(album['album_id']) : album['title'] for album in vk.get_albums()}

	result = sort_audios(audios, album_names)
	if debug_mode:
		save_audios(result, result_dump)

	if result[0]['aid'] != audios[0]['aid']:
		vk.reorder_audio(result[0]['aid'], before=audios[0]['aid'])
	for i, audio in enumerate(result[1:], 1):
		vk.reorder_audio(audio['aid'], after=result[i - 1]['aid'])


main(email=email, password=password)

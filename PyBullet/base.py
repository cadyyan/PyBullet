import pybullet.auth

import json
import mimetypes
import os.path
import websocket

class Client(object):
	"""
	PushBullet client for Python.
	"""

	GLOBAL_SETTINGS_FILE = os.path.expanduser('~/.pybulletrc')

	BASE_URL      = 'https://api.pushbullet.com/v2'
	CONTACTS_URL  = BASE_URL + '/contacts'
	DEVICE_URL    = BASE_URL + '/devices'
	ME_URL        = BASE_URL + '/users/me'
	PUSH_URL      = BASE_URL + '/pushes'
	UPLOAD_URL    = BASE_URL + '/upload-request'

	def __init__(self, settings = None):
		"""
		Creates a client based off of the given settings. The settings parameter
		can be a string that points to a JSON file or it can be dictionary of
		setting values. These settings override the "Global settings" that are
		set per user via the GLOBAL_SETTINGS_FILE.
		"""

		if not os.path.exists(Client.GLOBAL_SETTINGS_FILE) and not settings:
			raise Exception('No settings given')

		if os.path.exists(Client.GLOBAL_SETTINGS_FILE):
			self.settings = Client._load_config()
		else:
			self.settings = {}

		if settings:
			if isinstance(settings, str):
				settings = Client._load_config(settings)

			self.settings.update(settings)

		auth_settings = self.settings['auth']
		if auth_settings['type'] == 'basic':
			self.auth = pybullet.auth.BasicAuthenticator(auth_settings)
		elif auth_settings['type'] == 'oauth':
			self.auth = pybullet.auth.OAuthAuthenticator(auth_settings)
		else:
			raise Exception('Invalid authentication scheme given. Must be basic or oauth')

	def devices(self):
		"""
		List devices.
		"""

		resp = self.auth.send_request(Client.DEVICE_URL, 'GET')

		return resp['devices']

	def create_device(self, name, device_type):
		"""
		Create a device.
		"""

		resp = self.auth.send_request(
			Client.DEVICE_URL,
			'POST',
			data = {
				'type': device_type,
				'nickname': name,
			},
		)

		return resp

	def update_device(self, device_iden, **kwargs):
		"""
		Update an existing device. kwargs gives the values that will be updated.
		"""

		return self.auth.send_request(
			Client.DEVICE_URL + '/' + device_iden,
			'POST',
			data = kwargs,
		)

	def delete_device(self, device_iden):
		"""
		Delete the given device.
		"""

		self.auth.send_request(Client.DEVICE_URL + '/' + device_iden, 'DELETE')

	def push(self, push_type, **kwargs):
		"""
		Push to a specific device, all devices, or a user. Pushes come in several type
		and each type requires different parameters. These types and their
		parameters are:

		push_type = note
			* title - note's title
			* body  - note's message

		push_type = link
			* title - the link's title
			* url   - the url to open
			* body  - optional message

		push_type = address
			* name    - the place's name
			* address - the places'address or map search query

		push_type = list
			* title - the list's title
			* items - the list of items

		push_type = file
			* file_name - the name of the file
			* file_type - the MIME type of the file
			* file_url  - the url where the file can be downloaded
			* body      - message to with the file

		All push types also take a device_iden or email paramter to push to a
		device or user. If device_iden is not given the push goes to all devices.

		To push a file you must first upload it using the upload_file method.
		"""

		kwargs['type'] = push_type

		return self.auth.send_request(Client.PUSH_URL, 'POST', data = kwargs)

	def push_history(self, modified_timestamp):
		"""
		Get all the pushes that were created/modified after the given
		UNIX timestamp.
		"""

		return self.auth.send_request(
			Client.PUSH_URL,
			'GET',
			params = {'modified_after': modified_timestamp},
		)['pushes']

	def dismiss_push(self, push_iden):
		"""
		Dismiss a push
		"""

		return self.auth.send_request(
			Client.PUSH_URL + '/' + push_iden,
			'POST',
			data = {'dismissed': 'true'}
		)

	def delete_push(self, push_iden):
		"""
		Delete a push
		"""

		self.auth.send_request(
			Client.PUSH_URL + '/' + push_iden,
			'DELETE',
		)

	def contacts(self):
		"""
		Get contacts
		"""

		return self.auth.send_request(
			Client.CONTACTS_URL,
			'GET',
		)

	def create_contact(self, name, email):
		"""
		Create a new contact
		"""

		return self.auth.send_request(
			Client.CONTACTS_URL,
			'POST',
			data = {'name': name, 'email': email},
		)

	def update_contact(self, contact_iden, **kwargs):
		"""
		Update contact information
		"""

		return self.auth.send_request(
			Client.CONTACTS_URL + '/' + contact_iden,
			'POST',
			data = kwargs,
		)

	def delete_contact(self, contact_iden):
		"""
		Delete contact
		"""

		self.auth.send_request(
			Client.CONTACTS_URL + '/' + contact_iden,
			'DELETE',
		)

	def me(self):
		"""
		Get information about the current user
		"""

		return self.auth.send_request(Client.ME_URL, 'GET')

	def update_me(self, **kwargs):
		"""
		Update current user preferences
		"""

		return self.auth.send_request(
			Client.ME_URL,
			'POST',
			headers = {'content-type': 'application/json'},
			data = json.dumps(kwargs),
		)

	def upload_file(self, inputfile, filename = None, file_type = None):
		"""
		Upload a file. The inputfile parameter can be a file path string
		or a file handle. If you give a file handle you can override the
		filename that is sent to PushBullet. We try to guess the MIME type
		of the file but you can override that as well.
		"""

		file_handle = open(inputfile, 'rb') if isinstance(inputfile, str) else inputfile
		name        = filename or file_handle.name
		mime_type   = file_type or mimetypes.guess_type(name)

		resp = self.auth.send_request(
			Client.UPLOAD_URL,
			'POST',
			data = {'file_name': name, 'file_type': mime_type}
		)

		self.auth.send_request(
			resp['upload_url'],
			'POST',
			skip_auth = True,
			data      = resp['data'],
			files     = {
				'file': file_handle,
			},
		)

		return resp

	@staticmethod
	def _load_config(settings = None):
		"""
		Load the configuration file.
		"""

		settings = settings or Client.GLOBAL_SETTINGS_FILE

		with open(settings, 'r') as fh:
			return json.load(fh)


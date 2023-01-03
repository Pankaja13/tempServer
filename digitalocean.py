import time
from datetime import datetime

from pydo import Client


class DigitalOcean:

	def __init__(self, token, temp_server_name, ssh_key_names, region, starter_image, droplet_size):
		self.client = Client(token=token)
		self.TEMP_SERVER_NAME = temp_server_name
		self.SSH_KEY_NAMES = ssh_key_names
		self.REGION = region
		self.STARTER_IMAGE = starter_image
		self.DROPLET_SIZE = droplet_size

	def get_ssh_keys(self):
		keys = []

		resp = self.client.ssh_keys.list(per_page=50)
		for k in resp["ssh_keys"]:
			if k["name"] in self.SSH_KEY_NAMES:
				keys.append(k)
		return keys

	def create_temp_droplet(self):
		this_response = self.client.droplets.create(body={
			"name": self.TEMP_SERVER_NAME,
			"region": self.REGION,
			"size": self.DROPLET_SIZE,
			"image": self.STARTER_IMAGE,
			"ssh_keys": [key['fingerprint'] for key in self.get_ssh_keys()],
		})
		return this_response

	def get_temp_droplet(self, wait_for_online=False):
		try:
			my_droplets = self.client.droplets.list()['droplets']
		except KeyError:
			return False
		temp_droplets = [droplet for droplet in my_droplets if self.TEMP_SERVER_NAME in droplet['name']]
		if not temp_droplets:
			return None

		if len(temp_droplets) > 1:
			raise ValueError("Too many temp droplets active")

		this_droplet = temp_droplets[0]

		if wait_for_online:
			while not this_droplet['networks']['v4']:
				time.sleep(1)
				this_droplet = self.get_temp_droplet()

		return temp_droplets[0]

	def wait_for_action(self, action_id, wait=5):
		print('Waiting', end="", flush=True)

		status = "in-progress"
		while status == "in-progress":
			print('.', end="", flush=True)

			resp = self.client.actions.get(action_id)

			status = resp["action"]["status"]
			if status == "in-progress":
				time.sleep(wait)
			elif status == "errored":
				raise Exception(f"{resp['action']['id']} action {resp['action']['id']} {status}")
		print("")

	def get_snapshot(self):
		sorted_snapshots = self.get_snapshots()

		try:
			return sorted_snapshots[0]
		except IndexError:
			return None

	def get_snapshots(self):
		try:
			snapshots: list = self.client.snapshots.list()['snapshots']
		except KeyError:
			return None

		snapshots = [
			{
				'name': snapshot['name'],
				'date': datetime.strptime(snapshot['created_at'], '%Y-%m-%dT%H:%M:%SZ'),
				'id': snapshot['id']
			}
			for snapshot in snapshots if self.TEMP_SERVER_NAME in snapshot['name']
		]

		return sorted(snapshots, key=lambda d: d['date'], reverse=True)

	def delete_snapshot(self, snapshot_id):
		self.client.snapshots.delete(snapshot_id)

	def create_snapshot(self, droplet_id):
		response = self.client.droplet_actions.post(droplet_id, body={
			'type': 'snapshot'
		})
		return response

	def destroy_temp_droplet(self):
		this_droplet = self.get_temp_droplet(True)
		try:
			self.client.droplets.destroy(this_droplet['id'])
		except (KeyError, TypeError):
			print("Droplet doesn't exist")

	def check_action(self, action_id):
		action_response = self.client.actions.get(action_id)
		return action_response['action']['status'] == "completed"

	def trim_snapshots(self):
		snapshots = self.get_snapshots()
		snapshots = snapshots[3:]
		print(f"Flushing {len(snapshots)} snapshots")
		for snapshot in snapshots:
			self.delete_snapshot(snapshot['id'])

	def up(self):
		droplet = self.get_temp_droplet()

		if not droplet:
			latest_snapshot = self.get_snapshot()

			if not latest_snapshot:
				print("Creating droplet from scratch")
				create_response = self.create_temp_droplet()
				self.wait_for_action(create_response['links']['actions'][0]['id'])
			else:
				print('Snapshot found')
				create_response = self.create_droplet_from_snapshot(latest_snapshot['id'])
				self.wait_for_action(create_response['links']['actions'][0]['id'])
				print('Droplet created from snapshot')

		droplet = self.get_temp_droplet()
		print(droplet)

	def down(self):
		droplet = self.get_temp_droplet(True)
		snapshot_response = self.create_snapshot(droplet['id'])
		action_id = snapshot_response['action']['id']
		self.wait_for_action(action_id)
		if self.check_action(action_id):
			print("Destroying Droplet")
			self.destroy_temp_droplet()
		self.trim_snapshots()

	def create_droplet_from_snapshot(self, snapshot_id):
		this_response = self.client.droplets.create(body={
			"name": self.TEMP_SERVER_NAME,
			"region": self.REGION,
			"size": "s-1vcpu-1gb",
			"image": snapshot_id,
		})
		return this_response

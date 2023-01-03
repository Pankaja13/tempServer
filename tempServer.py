import click

import digitalocean
from env import KEY, TEMP_SERVER_NAME, SSH_KEY_NAMES, REGION, STARTER_IMAGE, DROPLET_SIZE

do = digitalocean.DigitalOcean(
	token=KEY,
	temp_server_name=TEMP_SERVER_NAME,
	ssh_key_names=SSH_KEY_NAMES,
	region=REGION,
	starter_image=STARTER_IMAGE,
	droplet_size=DROPLET_SIZE
)


@click.group()
def cli():
	pass


@cli.command()
def up():
	do.up()


@cli.command()
def down():
	do.down()


if __name__ == '__main__':
	cli()

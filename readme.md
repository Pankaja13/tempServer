# tempServer
CLI for server archiving on Digital Ocean

Setup

```shell
sudo nano env.py
poetry install
poetry run python tempServer.py --help

# start your first droplet / restore from snapshot
poetry run python tempServer.py up

# see droplet status
poetry run python tempServer.py status

# snapshot, archive and destroy droplet
poetry run python tempServer.py down
```


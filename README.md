# Scaife Viewer

The new reading environment for version 5.0 of the Perseus Digital Library.

This repository is part of the [Scaife Viewer](https://scaife-viewer.org) project, an open-source ecosystem for building rich online reading environments.

## Getting Started with Codespaces Development

This project can be developed via [GitHub Codespaces](https://github.com/features/codespaces).

### Setting up the Codespace
- Browse to https://github.com/scaife-viewer/scaife-viewer
- (Optionally) fork the repo; if you're a part of the Scaife  Viewer development team, you can work from `scaife-viewer/scaife-viewer`
- Create a codespace from the green "Code" button:
  ![image-20230622050539589](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622050539589.png)
- Configure options to:
  - Choose the closest data center to your geographical location
  - Start the codespace from the `feature/content-update-pipeline` branch
  ![image-20230622050632620](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622050632620.png)

### Install and build the frontend
- Install and activate Node 12:
```shell
nvm use 12
```
- Install dependencies:
```shell
npm i
```
- Rebuild the `node-sass` dependency:
```shell
npm rebuild node-sass
```
- Build the frontend:
```shell
npm run build
```


### Start up PostgreSQL and ElasticSearch
_Note_: These may be made optional in the future
Build and start up services via:
```shell
touch deploy/.env
docker-compose -f deploy/docker-compose.yml up -d sv-elasticsearch sv-postgres
```
### Prepare the backend
- Create a virtual environment and activate it:
```shell
python3 -m venv .venv
source .venv/bin/activate
```
- Install dependencies:
```shell
pip install pip wheel --upgrade
pip install -r requirements.txt
pip install PyGithub
```
- Set required environment variables:
```shell
export CTS_RESOLVER=local \
    CTS_LOCAL_DATA_PATH=data/cts \
    CONTENT_MANIFEST_PATH=data/content-manifests/test.yaml \
    DATABASE_URL=postgres://scaife:scaife@127.0.0.1:5432/scaife
```

- Populate the database schema and load site fixture:
```shell
./manage.py migrate
./manage.py loaddata sites
```
- Copy the static assets
```shell
./manage.py collectstatic --noinput
```

- Fetch content from `content-manifests/test.yaml`:
```shell
mkdir -p $CTS_LOCAL_DATA_PATH
./manage.py load_text_repos
./manage.py slim_text_repos
```
- Ingest the data and pre-populate CTS cache:
```shell
mkdir -p atlas_data
./manage.py prepare_atlas_db --force
```

### Seed the search index
We'll ingest a portion of the data into ElasticSearch

- Fetch the ElasticSearch template:
```shell
curl -O https://gist.githubusercontent.com/jacobwegner/68e538edf66539feb25786cc3c9cc6c6/raw/3d17cde6a72d4526aa15fe79a07265c6638dd71c/scaife-viewer-tmp.json
```
- Install the template:
```shell
curl -X PUT "localhost:9200/_template/scaife-viewer?pretty" -H 'Content-Type: application/json' -d "$(cat scaife-viewer-tmp.json)"
```
- Index content:
```shell
python manage.py indexer --max-workers=1 --limit=1000
```
- Cleanup the search index template:
```shell
rm scaife-viewer-tmp.json
```

### Run the dev server
```shell
 ./manage.py runserver
```

Codespaces should show a notification that a port has been mapped:
![image-20230622052553784](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622052553784.png)
- Click "Open in Browser" to load the dev server.
- Click on "try the Iliad" to load the reader:
  ![image-20230622054959080](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622054959080.png)

The Codespace has now been set up!  Close it by opening the "Codespaces" menu (`F1`) and then selecting
`Codespaces: Stop Current Codespace`.

### Rename the Codepsace
- Browse to https://github.com/codespaces and find the codespace:
  ![image-20230622165419317](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622165419317.png)
- Select the "..." menu and then "Rename":
  ![image-20230622165552978](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622165552978.png)
- Give the Codespace a meaningful name (e.g. Scaife Viewer / Perseus dev):
  ![image-20230622165414325](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622165414325.png)


### Ongoing development
- Browse to https://github.com/codespaces and find the codespace
- Select the "..." menu and then "Open in..." and select "Open in browser" or another of the available options.
  ![image-20230622165503906](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622165503906.png)
- After the Codespace launches, open a new terminal and reactivate the Python virtual environment:
```shell
source .venv/bin/activate
```
- Populate required envionment variables:
```shell
export CTS_RESOLVER=local \
    CTS_LOCAL_DATA_PATH=data/cts \
    CONTENT_MANIFEST_PATH=data/content-manifests/test.yaml \
    DATABASE_URL=postgres://scaife:scaife@127.0.0.1:5432/scaife
```
- Start up PostgreSQL and ElasticSearch:
```shell
docker-compose -f deploy/docker-compose.yml up -d sv-elasticsearch sv-postgres
# Optionally wait 10 seconds for Postgres to finish starting
sleep 10
```
- Run the dev server:
```shell
 ./manage.py runserver
```
Codespaces should show a notification that a port has been mapped:
![image-20230622052553784](https://f000.backblazeb2.com/file/typora-images-23-06-14/uPic/image-20230622052553784.png)
- Click "Open in Browser" to load the dev server.

## Getting Started with Local Development
<!-- TODO: Update this section of the docs; Codespaces documentation is more up to date. -->
Requirements:

* Python 3.6.x
* Node 11.7
* PostgreSQL 9.6
* Elasticsearch 6

First, install and run Elasticsearch on port 9200. If you're on a Mac, we recommend using brew for this:

    brew install elasticsearch
    brew services start elasticsearch

Then, set up a postgres database to use for local development:

    createdb scaife-viewer

This assumes your local PostgreSQL is configured to allow your user to create databases. If this is not the case you might be able to create the user yourself:

    createuser --username=postgres --superuser $(whoami)

Create a virtual environment. Then, install the Node and Python dependencies:

    npm install
    pip install -r requirements-dev.txt

Set up the database:

    python manage.py migrate
    python manage.py loaddata sites

Seed the text inventory to speed up local development:

    ./bin/download_local_ti

You should now be set to run the static build pipeline and hot module reloading:

    npm start

In another terminal, collect the static files and then start runserver:

    python manage.py collectstatic --noinput
    python manage.py runserver

Browse to http://localhost:8000/.

Note that, although running Scaife locally, this is relying on the Nautilus server at https://scaife-cts-dev.perseus.org to retrieve texts.

## Tests

You can run the Vue unit tests, via:

    npm run unit

Cross-browser testing is provided by BrowserStack through their [open source program](](https://www.browserstack.com/open-source)).  

## Translations

Before you work with translations, you will need gettext installed.

macOS:

    brew install gettext
    export PATH="$PATH:$(brew --prefix gettext)/bin"

To prepare messages:

    python manage.py makemessages --all

If you need to add a language; add it to `LANGUAGES` in settings.py and run:

    python manage.py makemessages --locale <lang>

## Hosting Off-Root

If you need to host at a place other than root, for example, if you need to have
a proxy serve at some path off your domain like http://yourdomain.com/perseus/,
you'll need to do the following:

1. Set the environment variable, `FORCE_SCRIPT_NAME` to point to your script:

```
    export FORCE_SCRIPT_NAME=/perseus  # this front slash is important
```

2. Make sure this is set prior to running `npm run build` as well as prior to and
   part of your wsgi startup environment.

3. Then, you just set your proxy to point to the location of where your wsgi
   server is running.  For example, if you are running wsgi on port 8000 you can
   have this snippet inside your nginx config for the server:

```
    location /perseus/ {
        proxy_pass        http://localhost:8000/;
    }
```

That should be all you need to do.

## Deploying via Docker

A sample docker-compose configuration is available at `deploy/docker-compose.yml`.

Copy `.env.example` and customize environment variables for your deployment:

```
cp deploy/.env.example deploy/.env
```

To build the Docker image and bring up the `scaife-viewer`, `sv-postgres` and `sv-elasticsearch` services in the background:

```
docker-compose -f deploy/docker-compose.yml up --build -d
```

Tail logs via:

```
docker-compose -f deploy/docker-compose.yml logs --follow
```

To host the application off-root using docker-compose, you'll need to ensure that the `scaife-viewer` Docker image is built with the `FORCE_SCRIPT_NAME` build arg:

```
docker-compose -f deploy/docker-compose.yml build --build-arg FORCE_SCRIPT_NAME=/<your-off-root-path>
```

You'll also need to ensure that `FORCE_SCRIPT_NAME` exists in `deploy/.env`:

```
echo "FORCE_SCRIPT_NAME=/<your-off-root-path>" >> deploy/.env
```

Then, bring up all services:

```
docker-compose -f deploy/docker-compose.yml up -d
```

## Using Docker for development

The project also includes `Dockerfile-dev` and `Dockerfile-webpack` images which can be used with Docker Compose to facilitate development.

First, copy `.env.example` and customize environment variables for development:

```
cp deploy/.env.example deploy/.env
```

Then build the images and spin up the containers:

```
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.override.yml up --build
```

To run only the `scaife-viewer`, `sv-webpack`, and `sv-postgres` services, set the `USE_ELASTICSEARCH_SERVICE` environment variable in `docker-compose.override.yml` to 0, and then run:

```
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.override.yml up --build scaife-viewer sv-webpack sv-postgres
```

To run the indexer command:

```
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.override.yml exec scaife-viewer python manage.py indexer
```

## API Library Cache

The client-side currently caches the results of `library/json/`. The cache is automatically invalidated every 24 hours. You can manually invalidate it by bumping the `LIBRARY_VIEW_API_VERSION` environment variable.

## ATLAS Database

`bin/fetch_atlas_db` can be used to fetch and extract an ATLAS database from a provided URL.

To build a copy of this database locally:
- Run `bin/download_local_ti` to get a local copy of the text inventory from `$CTS_API_ENDPOINT`
- Run `bin/fetch_corpus_config` to load corpus-specific configuration files
- Run the `prepare_atlas_db` management command to ingest ATLAS data from CTS collections (assumes `atlas_data` directory exists; create it via `mkdir -p atlas_data`)

Queries to ATLAS models are routed via the `ATLASRouter` database router
(and therefore are isolated from the `default` database)

## CTS Data

CTS data is now bundled with the application.

The deployment workflow is responsible for making corpora available under at the location
specified by `settings.CTS_LOCAL_DATA_PATH`.

For Heroku deployments, this is currently accomplished by preparing a tarball made available via
`$CTS_TARBALL_URL` and downloading and uncompressing the tarball using `bin/fetch_cts_tarball.sh`.

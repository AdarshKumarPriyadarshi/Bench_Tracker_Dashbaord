# Getting Started

## Installation

Dr. Burn can be installed either as [binary](#binary) (recommended), from [source](#source) or run as [Docker container](#docker) (experimental)

### Binary

Find the latest binary on Dr. Burn's [GitLab Releases](https://git.swf.daimler.com/adasdai/drburn/-/releases) Page and
download from artifactory.

1. Make `drburn` executable
   ```ssh
   chmod +x drburn
   ```
2. Run `drburn`
   ```ssh
   ./drburn
   ```

### Source

1. Clone the repository
   ```ssh
   git clone ssh://git@git.swf.daimler.com:7999/adasdai/drburn.git
   ```
2. Change current working dir
   ```ssh
   cd drburn
   ```
3. Run `drburn`
   ```ssh
   ./drburn
   ```

> If `drburn` has issues finding dependencies, then [reinstall the virtualenv](#reinstall-the-virtualenv).

#### Reinstall the virtualenv

1. Create the virtualenv
   ```ssh
   python -m venv src/venv
   ```
   > Depending on your distribution you may have to issue the following command:
   ```ssh
   python3 -m venv src/venv
   ```
2. Activate the virtualenv
   ```ssh
   source src/venv/bin/activate
   ```
3. Install dependencies
   ```ssh
   pip install -r requirements.txt
   ```
4. Run `drburn`
   ```ssh
   ./drburn
   ```

### Docker

1. Run the container

```shell
docker run -it --rm --net=host artifact.swf.i.mercedes-benz.com/adasdai-docker/drburn:latest ./drburn "<arguments>"
```

> Currently, only some features will work out-of-the box by issuing that command. For some flash operations
> Dr. Burn's container needs to be setup for DinD (Docker-in-Docker). Also flashing locally stored tarballs requires
> that folder locations to be mounted as volumes.

## Development

### Activate virtualenv

> Currently, the virtualenv is committed to `src/venv` for convenience running on a specific mttf testbench.
> For local development you can install your own virtualenv and exclude the committed one in your IDE.

```shell
./src/venv/bin/activate
```

### Run tests

```shell
pytest
```

## Docker

### Build

Build the image locally

```shell
docker build -t drburn .
```

or

```shell
docker compose build drburn
```

### Run

Run the container

```shell
docker run -it --rm --net=host artifact.swf.i.mercedes-benz.com/adasdai-docker/drburn:latest ./drburn "<arguments>"
```

or

```shell
mkdir ./test_results
docker run -it --rm --net=host --name drburn -v $(pwd):/repo -w /repo drburn ./drburn "<arguments>"
```

or

```shell
docker compose run drburn ./drburn "<arguments>"
```

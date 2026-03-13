# Backend API
## To run docker container (for deployment):
```bash
docker build -t ad-detection-api .
docker run -d -p 5000:5000 
  -v "/home/irisglaze/MitmProxyAdFiles/extracted_texts.db:/app/data/extracted_texts.db" \
  ad-detection-api

```
To run docker container for production:
```bash
docker run -d --name ad-detection-api-docker -p 5000:5000 -v /home/irisglaze/MitmProxyAdFiles:/app/data ad-detection-api
```
... and repace ```/home/irisglaze/MitmProxyAdFiles``` with your local directory path where main project data is stored.

## To run the Flask application (locally):
```bash
python -m flask run
```
## This file can be populated with image file paths to limit images shown in the website questionnaire.
```input/allowed_image_filepaths.txt```

## Making MitmProxyAdFiles available at /app/data
The image already creates the target directory `/app/data` at build time. Here are three safe ways to get your `../MitmProxyAdFiles` directory into the container so the app can read those files.

1) Preferred: mount the host directory at runtime (no rebuild required)
```bash
# run from the project folder; replace the host path with the correct absolute path
docker run -d \
  --name ad-detection-api-docker \
  -p 5000:5000 \
  -v /absolute/path/to/MitmProxyAdFiles:/app/data \
  ad-detection-api
```
This is the simplest: the container sees the same files as the host and you can change files on the host without rebuilding.

2) Copy files into a running container (one-off)
```bash
# start the container (if not already running):
docker run -d --name ad-detection-api-docker -p 5000:5000 ad-detection-api
# copy files from a relative path into the container
# run from the host project parent directory, e.g. where ../MitmProxyAdFiles lives
docker cp ../MitmProxyAdFiles/. ad-detection-api-docker:/app/data
```
Use this if you need to push files into a running container without mounting volumes.

3) Build-time copy (only works if files are inside the build context)
Docker can only COPY files that are inside the build context. If `../MitmProxyAdFiles` is outside the context, first copy it into the repo or specify a different build context:
```bash
# option A: bring the files into the repo before building
cp -r ../MitmProxyAdFiles ./data
docker build -t ad-detection-api .

# option B: run docker build with a parent directory as the build context (careful: larger context)
# from the parent directory of the repo:
# docker build -f ad-detection-api/Dockerfile -t ad-detection-api ad-detection-api
```

Notes:
- On macOS and many CI systems you must use absolute host paths for `-v` mounts. In zsh use `$PWD` or `$(pwd)` if needed.
- The Dockerfile already contains `RUN mkdir -p /app/data` so `/app/data` will exist even if the volume is empty.
- If you need the container to write files back to the host, use a bind mount (the `-v` example above).

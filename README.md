# Backend API
## To run docker container (for deployment):
```bash
docker build -t ad-detection-api .
```
```bash
docker run -p 5000:5000 -v /home/irisglaze/MitmProxyAdFiles:/app/data ad-detection-api
```
... and repace ```/home/irisglaze/MitmProxyAdFiles``` with your local directory path where main project data is stored.

## To run the Flask application (locally):
```bash
python -m flask run
```
## This file can be populated with image file paths to limit images shown in the website questionnaire.
```input/allowed_image_filepaths.txt```


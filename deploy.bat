@ECHO OFF
ECHO Deploy an update to App Server
ECHO *** Run me from the Google Cloud SDK Shell! ***
set GOOGLE_APPLICATION_CREDENTIALS=resources\skraflhjalp-d20c6ea64ce2.json

REM gcloud beta app deploy --version=python3 --no-promote --project=skraflhjalp app.yaml
gcloud beta app deploy --version=python3 --promote --project=skraflhjalp app.yaml

ECHO Default module deployment completed

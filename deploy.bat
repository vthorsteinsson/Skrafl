@ECHO OFF
ECHO Deploy an update to App Server
ECHO *** Run me from the Google Cloud SDK Shell! ***
set GOOGLE_APPLICATION_CREDENTIALS=resources\skraflhjalp-d20c6ea64ce2.json
set PROJECT_ID=skraflhjalp

gcloud app deploy --no-cache --version=bin2024 --no-promote --project=skraflhjalp app.yaml

ECHO Default module deployment completed

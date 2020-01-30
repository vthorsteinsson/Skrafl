@ECHO OFF
ECHO Deploy an update to App Server
set PYTHONEXE=c:\python27\python
set CLOUD_SDK=%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk
set PYTHONPATH=%CLOUD_SDK%\platform\google_appengine
set APPCFG=%CLOUD_SDK%\platform\google_appengine\appcfg.py
ECHO Default module deployment starting
%PYTHONEXE% "%APPCFG%" update app.yaml --noauth_local_webserver
ECHO Default module deployment completed

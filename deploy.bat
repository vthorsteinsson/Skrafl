@ECHO OFF
ECHO Deploy an update to App Server
IF EXIST "c:\program files (x86)\google\google_appengine\appcfg.py" GOTO :X86
SET APPCFG="c:\program files\google\google_appengine\appcfg.py"
GOTO :CHECKS
:X86
SET APPCFG="c:\program files (x86)\google\google_appengine\appcfg.py"
:CHECKS
ECHO Default module deployment starting
%APPCFG% update app.yaml --noauth_local_webserver
ECHO Default module deployment completed

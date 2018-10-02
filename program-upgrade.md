# **WebCOOP Version Upgrade / Release Manual**
Copyright © 2018 | [EzTech Software and Consultancy Inc.](https://www.eztechsoft.com)
- - -
## **Upgrade Script**
#### WebCOOP is upgraded using the following bash script. (upgrade.sh)
```
#!/bin/bash

SOURCE_DIR="../data/custom/"
TEMP_DIR="~/temp/release"
APP1="13.228.36.174"
APP2="13.229.27.30"

python -m compileall $SOURCE_DIR
rm -rf TEMP_DIR/*
rsync -avz --include="__*.py" \
  --exclude=".*" \
  --exclude="*.py" \
  --exclude="*notes.txt" \
  --exclude="*.md" \
  $SOURCE_DIR $TEMP_DIR/

#stop the app servers
ssh $APP1 -i ~/MyCoopApp_KP.pem "cd /opt/webcoop && docker-compose stop app"
ssh $APP2 -i ~/MyCoopApp_KP.pem "cd /opt/webcoop && docker-compose stop app"

#copy the software remotely to the app servers
rsync -avz $TEMP_DIR/custom/webcoop/* $APP1:/opt/webcoop/data/webcoop/
rsync -avz $TEMP_DIR/custom/webcoop/* $APP2:/opt/webcoop/data/webcoop/

#restart the app servers
ssh $APP1 -i ~/MyCoopApp_KP.pem "cd /opt/webcoop && docker-compose restart app"
ssh $APP1 -i ~/MyCoopApp_KP.pem "cd /opt/webcoop && docker-compose restart app"
```
## **Procedure**
* Edit WebCOOP source code and test locally.
* After testing, run the upgrade-script upgrade.sh (needs AWS ssh certificate ~/myCoopApp_KP.pem).
* The application is now updated but the database data and views needs to be updated as well.
* Login as admin in WebCOOP.
* Upgrade the modified modules in Settings/Apps on all active databases.
- - -
### **Confidential**
*This document is proprietary and confidential. No part of this document may be disclosed in any manner to a third party without the prior written consent of Eztech Software and Consultancy Inc.*

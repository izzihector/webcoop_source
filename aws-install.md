# **WebCOOP Server Installation Guide**
Copyright © 2018 | [EzTech Software and Consultancy Inc.](https://www.eztechsoft.com)
- - -
## Application Server Installation

##### Set user as root and install some tools.
```
sudo su
yum install -y unzip \
  && yum install -y zip \
  && yum install -y epel-release \
  && yum install -y python-pip \
  && yum install -y nc \
  && yum install -y vim \
  && yum install -y nano \
  && pip install --upgrade pip
```
##### Install postgres client.
```
yum install -y \
  && https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-7-x86_64/pgdg-redhat96-9.6-3.noarch.rpm \
  && yum install -y postgresql96 \
  && yum install -y yum-utils device-mapper-persistent-data lvm2
```
##### Install docker.
```
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce
systemctl start docker
chkconfig docker on
pip install docker-compose
(Note: if you failed the install of docker-compose ,you cannot execute [docker-compose] command.maybe error message of [Command not found] will be shown in this case.
In this case ,you can follow below step.
1.downgrade pip to version 9.0.3
sudo pip install --upgrade --force-reinstall pip==9.0.3
2.install docker-compose
sudo pip install docker-compose
(please refer to https://github.com/docker/compose/issues/5883 for more details.)
)
```
##### Create the installation directory.
```
mkdir -p /opt/webcoop/data/logs
mkdir -p /opt/webcoop/data/webcoop
```
##### Create docker-compose.yml.
```
cat <<EOF > /opt/webcoop/docker-compose.yml
version: "2"
services:
  app:
    container_name: "webcoop"
    image: "zer0w1ng/odoo10:latest"
    restart: always
    ports:
      - 8069:8069
      - 8072:8072
    environment:
      - ODOO_RC=/var/lib/odoo/server.conf
    volumes:
      - ./data:/var/lib/odoo
    networks:
      - default_net

  web:
    container_name: "web_odoo10"
    image: "zer0w1ng/nginx:latest"
    restart: always
    volumes:
      - ./web.template:/etc/nginx/conf.d/mysite.template
    ports:
      - 80:80
    environment:
      - NGINX_PORT:80
    networks:
      - default_net

    command: /bin/sh -c "cat /etc/nginx/conf.d/mysite.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"

networks:
  default_net:
    driver: bridge

EOF
```
##### Create nginx config file.
```
cat <<EOF > /opt/webcoop/web.template

upstream odoo {
  server app:8069;
}

upstream odoochat {
  server app:8072;
}

server {
 listen 80;
 server_name _;

 if (\$http_x_forwarded_proto != "https") {
   rewrite ^(.*) https://\$host\$1 permanent;
 }

 client_max_body_size 200m;

 #timeouts
 proxy_read_timeout 720s;
 proxy_connect_timeout 720s;
 proxy_send_timeout 720s;
 send_timeout 600;
 keepalive_timeout 600;

 #gzip
 gzip on;
 gzip_disable "msie6";
 gzip_vary on;
 gzip_proxied any;
 gzip_comp_level 6;
 gzip_buffers 16 8k;
 gzip_http_version 1.1;
 gzip_types text/plain text/css application/json application/javascript
    application/x-javascript text/xml application/xml application/xml+rss
    application/rss+xml text/javascript image/svg+xml
    application/vnd.ms-fontobject application/x-font-ttf font/opentype
    image/bmp;

 add_header X-Frame-Options SAMEORIGIN;

 # Redirect requests to odoo backend server
 location / {

   proxy_pass http://odoo;

   # force timeouts if the backend dies
   proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;

   # Add Headers for odoo proxy mode
   proxy_set_header X-Forwarded-Host \$host;
   proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto \$scheme;
   proxy_set_header X-Real-IP \$remote_addr;
   proxy_set_header X-EzTech-Host \$host;
   #set_cookie_flag * HttpOnly secure;
   proxy_cookie_path / "/; secure";

   proxy_redirect off;
 }

 location /longpolling {
   proxy_pass http://odoochat;
 }

 location ~* /web/static/ {
   proxy_cache_valid 200 60m;
   proxy_buffering on;
   expires 864000;
   proxy_pass http://odoo;
 }

}

EOF
```
##### Create odoo config file.
```
cat <<EOF > /opt/webcoop/data/server.conf
[options]
addons_path = /mnt/extra-addons,/var/lib/odoo/webcoop,/usr/lib/python2.7/dist-packages/odoo/addons

admin_passwd = [admin-password>]
db_host = mycoopdbrds.ccfshrgpl98r.ap-southeast-1.rds.amazonaws.com
;change appropriate host name depending on the env
db_port = 5432
db_user = [db-username]
db_password = [db-password]
db_template = template0

#db-filter = ^%d.*$
dbfilter = ^%d.*$

xmlrpc = True

;Log Settings
logfile = /var/lib/odoo/logs/odoo.log
log_level = debug
#logrotate = True
#this logrotate doesn't work in case of multiporcess , so change it to using os's logrotate (20190827)

#proxy-mode = True
proxy_mode = True

;1048576 * 768 * workers
limit_memory_hard = 4831838208
;1048576 * 640 * workers
limit_memory_soft = 4026531840

limit_request = 8192
limit_time_cpu = 600
limit_time_real = 1200
max_cron_threads = 1
workers = 5

EOF
```
##### Change directory permissions.
```
chown -R centos.centos /opt/webcoop
chmod 777 /opt/webcoop/data
chmod 777 /opt/webcoop/data/logs
cd /opt/webcoop/data
find webcoop -type d -exec chmod 777 {} \;
```
##### Add user to docker group.
```
usermod -aG docker centos
```

##### Availe system logrotate for odoo.log(20190828 add suzuki)

1.Diable selinux
In case of centos7 on AWS,Selinux is enabled by default.But if selinux is enabled , system logrotate by cron will be failed , inspite  logrotate configuration is correct.reference:https://qiita.com/2no553/items/ac951b988d03cf520966).And selinux is not used and not necessary for current, so it need to be disabled for avoiding this logrotation problem and for avoiding too much security checking.Note:incase you need selinux, need to consider to create manual logrotation script on cron instead of using system logrotate.

sudo sed -i -e 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

2.Add config

sudo cat <<EOF > /etc/logrotate.d/odoo
/opt/webcoop/data/logs/odoo.log
{
    daily
    rotate 90
    ifempty
    missingok
    copytruncate
    compress
    su root root
    dateext
}
EOF

sudo logrotate /etc/logrotate.conf

3.system re-start

sudo shutdown now -r
(And wait about 5 minutes)


##### Re-login to server, then run docker compose script.
```
ssh -i private_key.pem centos@[app-server-address]
cd /opt/webcoop
docker-compose up -d
```

- - -
## File Server Installation

### Setup NFS Sharing.

##### Change user to root and Install NFS utilities.
```
sudo su
yum -y install nfs-utils
```
##### Then enable and start the NFS server service.
```
systemctl enable nfs-server.service
systemctl start nfs-server.service
```
##### Create share directory and set permissions.
```
mkdir -p /mnt/share/filestore
chown nfsnobody.nfsnobody /mnt/share
chown nfsnobody.nfsnobody /mnt/share/filestore
#add 20190831
chmod 777 /mnt/share/filestore
```
##### Add NFS IP address rights in [/etc/exports] The IP addresses are the local VPC addresses of the app servers.
```

/mnt/share/filestore        172.31.8.240(rw,sync,no_subtree_check)
/mnt/share/filestore        172.31.9.197(rw,sync,no_subtree_check)
(note: change 172.31.8.240 part to application server's private ip address)
```
##### Apply new exported NFS shares.
```
exportfs -a
```

##### Add the following line in /etc/fstab on the app server to connect to the NFS share. The IP address is the NFS server address.
```
172.31.25.176:/mnt/share/filestore /opt/webcoop/data/.local/share/ nfs rsize=8192,wsize=8192,timeo=14,intr
172.31.25.176:/mnt/share/filestore/odoolog/server1 /opt/webcoop/data/logs/ nfs rsize=8192,wsize=8192,timeo=14,intr
(172.31.25.176 is file server's ip)
(need to change "server1" to "server2" in case of server2)
```
##### Restart the app server.

### Setup Automated Backup

##### Create backup directory.
```
cd ~
mkdir -p backup
```

##### Create backup script file as `~/backup/backup.py`.
```
#!/usr/bin/env python

#########################################################################
import base64
import xmlrpclib
import time
import os
from dateutil.relativedelta import *
import glob
from datetime import datetime

def backupX(path, url, db, password):
    filename='%s/%s_%s.zip' % (path, db, time.strftime('%Y-%m-%d_%H%M%S'))

    print "Backup", filename

    sock = xmlrpclib.ServerProxy(url+"/xmlrpc/db")
    backup_file = open(filename, 'wb')
    dump = sock.dump(password, db, 'zip')
    backup_file.write(base64.b64decode(dump))
    backup_file.close()

def backup(path, url, db, password):
    filename='%s/%s_%s.zip' % (path, db, time.strftime('%Y-%m-%d_%H%M%S'))

    if 1:
        print "Backup", filename
        cmd = "curl -o %s -d master_pwd=%s -d name=%s %s/web/database/backup" % (
            filename,
            password,
            db,
            url,
        )

        print "CMD", cmd
        os.system(cmd)

    if 1:
        #delete old files
        now = datetime.now()
        dt_3months = now - relativedelta(months=3)
        #print dt_3months
        filename='%s/%s_%s*.zip' % (path, db, dt_3months.strftime('%Y-%m-%d'))
        files = glob.glob('%s/%s_*' % (path, db))
        for fn in files:
            if fn<filename:
                print "Deleting file", fn
                os.remove(fn)


#########################################################################

if __name__=="__main__":

    path = "<backup-storage-dir>"
    dbs = [
        '<list-of-db-to-backup>',
        ...
        ...
    ]

    for db in dbs:
        backup(
            path,
            "https://test.philippines-webcoop.com",
            db,
            "<master-password>",
        )
```

##### Create a cron file `cronz`.
Adjust the backup time if necessary depending on the server timezone.
Example is set at 13-UTC to start backup at 9PM Philippine time.
```
#min  hour  dom  month  dow  command
0     13    *    *      1-7  /home/centos/backup/backup.py >> /home/centos/backup.log
```

##### Set crontab of user by running the following command.
```
crontab ~/cronz
```

##### Backup script will now periodically run at the cron schedule.


- - -
## VPN Server Installation
##### Set user as root and install some tools.
```
sudo su
yum install -y unzip \
  && yum install -y zip \
  && yum install -y epel-release \
  && yum install -y python-pip \
  && yum install -y nc \
  && yum install -y vim \
  && yum install -y nano \
  && pip install --upgrade pip
```
##### Install docker.
```
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce
systemctl start docker
chkconfig docker on
pip install docker-compose
(Note: if you failed the install of docker-compose ,you cannot execute [docker-compose] command.maybe error message of [Command not found] will be shown in this case.
In this case ,you can follow below step.
1.downgrade pip to version 9.0.3
sudo pip install --upgrade --force-reinstall pip==9.0.3
2.install docker-compose
sudo pip install docker-compose
(please refer to https://github.com/docker/compose/issues/5883 for more details.)
)

```
##### Create the installation directory.
```
mkdir -p /opt/openvpn
```
##### Create docker-compose.yml file.
```
cat <<EOF > /opt/openvpn/docker-compose.yml
version: '2'
services:
  openvpn:
    cap_add:
      - NET_ADMIN
    image: kylemanna/openvpn
    container_name: openvpn
    ports:
      - "1194:1194/udp"
    restart: always
    volumes:
      - ./data/conf:/etc/openvpn
    networks:
      static-network:
        ipv4_address: 192.168.200.2

networks:
  static-network:
    ipam:
      config:
        - subnet: 192.168.200.0/24
          ip_range: 192.168.200.0/24

EOF
```
##### Change directory permissions.
```
chown -R centos.centos /opt/openvpn
```
##### Add user to docker group.
```
usermod -aG docker centos
```
##### Logout from server.
```
exit
exit
```
##### Re-login to server, then run docker compose script.
```
ssh -i private_key.pem centos@[vpn-server-address]
cd /opt/openvpn
docker-compose up -d
(Note: if you failed the install of docker-compose ,you cannot execute [docker-compose] command.maybe error message of [Command not found] will be shown in this case.
In this case ,you can follow below step.
1.downgrade pip to version 9.0.3
sudo pip install --upgrade --force-reinstall pip==9.0.3
2.install docker-compose
sudo pip install docker-compose
3.Then exit and re-login the server ,then  run docker compose script.
cd /opt/openvpn
docker-compose up -d
(please refer to https://github.com/docker/compose/issues/5883 for more details.)
)
```
##### Initialize the configuration files and certificates. Enter the paraphrase and remember it. (PEM paraphase: vxvY9g8cRfeVdcaR)
```
docker-compose run --rm openvpn ovpn_genconfig -u udp://vpn.philippines-webcoop.com
(change [udp://vpn.philippines-webcoop.com] to [udp://(vpn server's dns, or ip)]
docker-compose run --rm openvpn ovpn_initpki
(after above , you need to entry any passphrase. But you need to keep the passphrase for key createion. After that , you may be asked Common Name , but you can skip by blank.)
```
##### Create user client certiticate.
```
docker-compose exec openvpn easyrsa build-client-full [username] nopass
```
##### Retrieve the user client certificate.
```
docker-compose exec openvpn ovpn_getclient [username] > [username].ovpn
```
- - -
### **Confidential**
*This document is proprietary and confidential. No part of this document may be disclosed in any manner to a third party without the prior written consent of Eztech Software and Consultancy Inc.*

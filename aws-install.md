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
db_port = 5432
db_user = [db-username]
db_password = [db-password]
db_template = template0

db-filter = ^%d.*$

xmlrpc = True

;Log Settings
logfile = /var/lib/odoo/logs/odoo.log
log_level = debug
logrotate = True

proxy-mode = True

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
cd /opt/wecoop/data
find webcoop -type d -exec chmod 777 {} \;
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
ssh -i private_key.pem centos@[app-server-address]
cd /opt/webcoop
docker-compose up -d
```

- - -
## File Server Installation
##### Install NFS utilities.
```
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
```
##### Add NFS IP address rights in /etc/exports. The IP addresses are the local VPC addresses of the app servers.
```
/mnt/share/filestore        172.31.8.240(rw,sync,no_subtree_check)
/mnt/share/filestore        172.31.9.197(rw,sync,no_subtree_check)
```
##### Apply new exported NFS shares.
```
exportfs -a
```

#### Add the following line in /etc/fstab on the app server to connect to the NFS share. The IP address is the NFS server address.
```
172.31.25.176:/mnt/share/filestore /opt/webcoop/data/.local/share/ nfs rsize=8192,wsize=8192,timeo=14,intr
```
### Restart the app server.

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
```
##### Initialize the configuration files and certificates. Enter the paraphrase and remember it. (PEM paraphase: vxvY9g8cRfeVdcaR)
```
docker-compose run --rm openvpn ovpn_genconfig -u udp://vpn.philippines-webcoop.com
docker-compose run --rm openvpn ovpn_initpki
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

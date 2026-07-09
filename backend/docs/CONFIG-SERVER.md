# Configuration d'un serveur Ubuntu

## Prérequis
[Serveur]: Avoir un serveur type VPS pour récupérer les images
[Nginx]:
[Docker]

---

**Accéder au serveur**
Pour accéder à votre serveur, dans un terminal écrire la commande si dessous:
```bash
ssh user@ip_serveur
```

---

**Configuration serveur Ubuntu + Nginx**
```bash
sudo apt update
sudo apt upgrade
sudo apt install nginx ufw ca-certificates curl python-is-python3 python3-pip postgresql-client -y
```
---

***Installation Docker***
```bash
sudo install -m 0755 -d /etc/apt/keyrings
```
```bash
csudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
````
```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```
```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```
```bash
sudo apt update
```
```bash
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

Pour vérifier l'installation de Nginx, faire la commande suivante:
```bash
systemctl status nginx  
```

Autoriser le serveur le firewall pour Nginx et OpenSSH, puis activer le firewall et vérifier son statu
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

Après avoir autoriser le firewall, créer un fichier de configuration nginx, puis copier la configuration
```bash
nano /etc/nginx/site-avaible/file_name
```

```nginx
upstream backend_app  { server 127.0.0.1:8000; }

server {
    listen 80;
    server_name adress_ip;  # remplacer par un nom de domaine ou IP du serveur
    
    client_max_body_size 500M;

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    location /grafana/ {
    proxy_pass http://127.0.0.1:3001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebSocket pour Grafana Live (dashboards temps réel)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # Streams longs (Explore Loki/Tempo)
    proxy_read_timeout 300s;
    proxy_buffering off;
    }
    # Frontend SPA (catch-all)
    location / { proxy_pass http://backend_app; }
}
```

```bash
ln -s /etc/nginx/site-avaible/file_name /etc/nginx/site-enable/
nginx -t
systemctl status nginx
```
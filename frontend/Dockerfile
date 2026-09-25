# Vet-App FRONTEND — statik Mini App'lar (client, vet, admin) + Caddy.
# Caddy: avtomatik HTTPS (domen bo'lsa), /api va /admin'ni backend'ga yo'naltiradi,
# admin panelni IP bo'yicha cheklaydi.
FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY client /srv/client
COPY vet /srv/vet
COPY admin /srv/admin
COPY legal /srv/legal

EXPOSE 80 443 443/udp

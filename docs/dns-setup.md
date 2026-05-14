# DNS Setup — anjaneyaglobalrealty.com

DNS records to create before running `certbot`. Let's Encrypt will only
issue a certificate once these resolve to the droplet.

## Records

Set these at your domain registrar (or in DigitalOcean's DNS panel if
you've pointed the domain's nameservers at DigitalOcean):

| Type | Name  | Value                | TTL  | Notes                              |
| ---- | ----- | -------------------- | ---- | ---------------------------------- |
| A    | `@`   | `<droplet-ipv4>`     | 3600 | apex domain                        |
| A    | `www` | `<droplet-ipv4>`     | 3600 | www subdomain                      |
| AAAA | `@`   | `<droplet-ipv6>`     | 3600 | optional — only if the droplet has IPv6 |
| AAAA | `www` | `<droplet-ipv6>`     | 3600 | optional                           |

Replace `<droplet-ipv4>` / `<droplet-ipv6>` with the addresses shown in
the DigitalOcean droplet panel for `cspaces`.

## Verify before running certbot

```bash
dig +short anjaneyaglobalrealty.com        # → should return the droplet IPv4
dig +short www.anjaneyaglobalrealty.com    # → should return the droplet IPv4
```

Propagation is usually 5–30 minutes, occasionally up to 24 hours.

**Do not run `certbot` until both names resolve correctly.** Let's
Encrypt rate-limits failed validation attempts — running it against a
domain that doesn't resolve yet burns those attempts.

# GitHub Pages and Cloudflare setup for kalacun.com

GitHub account: **Kalacun**. Repository: **Kalacun/Kalacun.github.io**. Primary address: **https://kalacun.com**. The `www` address redirects to the primary address after DNS and HTTPS are ready.

## 1. Verify ownership of the domain

Open [GitHub account Settings → Pages](https://github.com/settings/pages). This is the account's settings page, not the repository's settings.

1. Under verified domains, choose **Add a domain**.
2. Enter **kalacun.com**.
3. GitHub displays a TXT record name and verification value.
4. In Cloudflare, select **kalacun.com → DNS → Records → Add record**.
5. Select **TXT**. Copy the exact name GitHub gives you (typically `_github-pages-challenge-Kalacun`) and its verification value. Set TTL to **Auto** and save.
6. Return to GitHub and choose **Verify** after the TXT record becomes visible. Keep the TXT record afterward.

The verification value is specific to your account; it must be copied from GitHub, not guessed. A TXT record does not have a proxy toggle. [GitHub's verification instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages).

## 2. Configure GitHub Pages before pointing DNS at it

Open [repository Settings → Pages](https://github.com/Kalacun/Kalacun.github.io/settings/pages).

- Under **Build and deployment → Source**, select **GitHub Actions**.
- Under **Custom domain**, enter **kalacun.com**, without `https://`, and save.
- The DNS check can fail at this stage because the website DNS records have not been added yet.

The repository's workflow builds the page automatically. If no run is pending, open [Actions](https://github.com/Kalacun/Kalacun.github.io/actions), choose **Check and publish website**, then **Run workflow** on `main`.

## 3. Add the Cloudflare website DNS records

Open **Cloudflare → kalacun.com → DNS → Records**. Add these five records, one at a time:

| Type | Name | Content / target | Proxy status | TTL |
| --- | --- | --- | --- | --- |
| A | `@` | `185.199.108.153` | DNS only (gray cloud) | Auto |
| A | `@` | `185.199.109.153` | DNS only (gray cloud) | Auto |
| A | `@` | `185.199.110.153` | DNS only (gray cloud) | Auto |
| A | `@` | `185.199.111.153` | DNS only (gray cloud) | Auto |
| CNAME | `www` | `kalacun.github.io` | DNS only (gray cloud) | Auto |

`@` means the root domain, `kalacun.com`. The `www` target is a hostname: do not add `https://`, a slash, or the repository name. Use **DNS only** so GitHub handles DNS validation and the HTTPS certificate directly. Cloudflare's proxy is not needed for this setup.

Keep existing **MX** records and email-related **TXT** records: this domain already uses Cloudflare email routing. Keep the GitHub verification TXT record too. Only replace conflicting website records for `@` or `www`, if any exist. Do not change nameservers or Cloudflare SSL modes for this DNS-only setup. No Cloudflare Pages project is needed.

For optional IPv6 support, also add these four **AAAA** records at `@`, each **DNS only**, TTL **Auto**:

```text
2606:50c0:8000::153
2606:50c0:8001::153
2606:50c0:8002::153
2606:50c0:8003::153
```

These addresses come from [GitHub's custom-domain documentation](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site). Cloudflare documents the [Add record controls here](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) and explains [DNS-only proxy status here](https://developers.cloudflare.com/dns/proxy-status/).

## 4. Enable HTTPS and check both addresses

Return to repository **Settings → Pages**. Once DNS succeeds and GitHub provisions its certificate, enable **Enforce HTTPS** if it is not already enabled.

Then check:

- **https://kalacun.com** displays the site.
- **https://www.kalacun.com** redirects to **https://kalacun.com**.
- The photo, CV, transcript, and certificate links open.
- The latest run in **Actions** finishes successfully.

DNS propagation and certificate provisioning can take up to 24 hours. Do not repeatedly replace working records while waiting. Ordinary content updates usually need only the GitHub workflow to complete, without DNS or certificate changes.

## 5. Check DNS from Terminal if needed

```bash
dig +short kalacun.com A
dig +short www.kalacun.com CNAME
dig +short _github-pages-challenge-Kalacun.kalacun.com TXT
```

The first command should show GitHub's four IPv4 addresses. The second should show `kalacun.github.io.`. For the third, use the exact challenge record name GitHub supplied if it differs.

If HTTPS remains unavailable, check for conflicting root A/AAAA records or a `www` record pointing elsewhere, an orange Cloudflare cloud, or restrictive CAA records. If CAA records are present, GitHub requires permission for `letsencrypt.org`; do not alter unrelated email records. [GitHub troubleshooting](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages).

If you later remove this GitHub Pages site, remove or update its website DNS records and custom-domain association as part of that change. Keep the ownership-verification TXT record while using the domain with this account.

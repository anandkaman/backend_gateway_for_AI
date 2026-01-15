# External Access Security Guide

## Quick Answer

**For Testing:** ❌ No certificate needed - HTTP works fine  
**For Production:** ✅ SSL/TLS certificate required - Use HTTPS

---

## HTTP vs HTTPS

### HTTP (No Certificate) - Testing Only

**What you have now:**
```
http://106.51.48.79:8080
```

**Pros:**
- ✅ Works immediately
- ✅ No setup required
- ✅ Good for testing

**Cons:**
- ❌ **Data sent in plain text** (anyone can read it)
- ❌ **Passwords visible** on network
- ❌ **Images/files not encrypted**
- ❌ **Not secure for production**

**Use for:**
- Internal testing
- Development
- Trusted networks only

### HTTPS (With Certificate) - Production

**What you need:**
```
https://your-domain.com
```

**Pros:**
- ✅ **All data encrypted**
- ✅ **Passwords protected**
- ✅ **Images/files secure**
- ✅ **Browser shows padlock 🔒**
- ✅ **Production-ready**

**Cons:**
- Requires domain name
- Requires SSL certificate
- Extra setup needed

**Use for:**
- Production deployments
- Public APIs
- Sensitive data

---

## Do You Need a Certificate?

### ✅ YES - You NEED HTTPS if:

1. **Sending sensitive data** (passwords, personal info, documents)
2. **Public internet access** (anyone can connect)
3. **Production environment**
4. **Compliance requirements** (GDPR, HIPAA, etc.)
5. **Mobile apps** (iOS/Android require HTTPS)

### ❌ NO - HTTP is OK if:

1. **Testing only** (temporary)
2. **Internal network** (VPN, private network)
3. **Localhost development**
4. **Trusted users only**

---

## Current Setup: HTTP (No Certificate)

Your gateway is currently accessible via:

```
http://106.51.48.79:8080
```

**Security Status:**
- ⚠️ **Not encrypted** - Data visible on network
- ⚠️ **JWT tokens visible** - Can be intercepted
- ⚠️ **Images visible** - OCR data not protected

**Recommendation:**
- ✅ OK for testing
- ❌ NOT OK for production

---

## How to Add HTTPS (3 Options)

### Option 1: Free SSL with Let's Encrypt (Recommended)

**Requirements:**
- Domain name (e.g., `api.yourcompany.com`)
- Nginx reverse proxy

**Steps:**

1. **Point domain to your VPS:**
   ```
   A Record: api.yourcompany.com → 106.51.48.79
   ```

2. **Install Nginx:**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```

3. **Configure Nginx:**
   ```nginx
   # /etc/nginx/sites-available/ai-gateway
   server {
       listen 80;
       server_name api.yourcompany.com;
       
       location / {
           proxy_pass http://localhost:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. **Get SSL certificate (FREE):**
   ```bash
   sudo certbot --nginx -d api.yourcompany.com
   ```

5. **Done!** Your API is now:
   ```
   https://api.yourcompany.com
   ```

**Cost:** FREE  
**Time:** 15 minutes  
**Auto-renewal:** Yes

### Option 2: Cloudflare (Easiest)

**Steps:**

1. **Sign up at cloudflare.com** (free)
2. **Add your domain**
3. **Point DNS to your VPS**
4. **Enable SSL/TLS** (click one button)

**Pros:**
- ✅ Easiest setup
- ✅ Free SSL
- ✅ DDoS protection
- ✅ CDN included

**Cons:**
- Requires domain name

### Option 3: Self-Signed Certificate (Not Recommended)

**Only for internal testing:**

```bash
# Generate self-signed cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nginx-selfsigned.key \
  -out /etc/ssl/certs/nginx-selfsigned.crt
```

**Cons:**
- ❌ Browser warnings
- ❌ Not trusted
- ❌ Manual acceptance needed

---

## Comparison with SSH

### SSH (Port 22)
- ✅ Always encrypted
- ✅ Certificate-based authentication
- ✅ Secure by default
- Used for: Server access

### HTTP (Port 8080) - Current
- ❌ Not encrypted
- ❌ No certificate
- ❌ Plain text
- Used for: API access (testing)

### HTTPS (Port 443) - Recommended
- ✅ Encrypted (like SSH)
- ✅ Certificate-based
- ✅ Secure
- Used for: API access (production)

**Think of HTTPS as "SSH for web APIs"**

---

## Quick Setup Guide (15 minutes)

### If you have a domain name:

```bash
# 1. Install Nginx + Certbot
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y

# 2. Create Nginx config
sudo nano /etc/nginx/sites-available/ai-gateway

# Paste this:
server {
    listen 80;
    server_name YOUR_DOMAIN.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # File upload size limit
        client_max_body_size 10M;
    }
}

# 3. Enable site
sudo ln -s /etc/nginx/sites-available/ai-gateway /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 4. Get FREE SSL certificate
sudo certbot --nginx -d YOUR_DOMAIN.com

# 5. Done! Test it:
curl https://YOUR_DOMAIN.com/health
```

### If you DON'T have a domain:

**Option A: Use HTTP for testing**
```
http://106.51.48.79:8080
```
⚠️ Not secure, but works

**Option B: Get a free domain**
- freenom.com (free .tk, .ml domains)
- afraid.org (free subdomains)
- noip.com (free DNS)

---

## Security Best Practices

### For Testing (HTTP):

1. ✅ Use strong JWT secret
2. ✅ Limit access by IP (firewall)
3. ✅ Don't send real sensitive data
4. ✅ Use VPN if possible

### For Production (HTTPS):

1. ✅ Use HTTPS only
2. ✅ Strong JWT secret (512-bit)
3. ✅ Rate limiting enabled
4. ✅ Firewall configured
5. ✅ Regular security updates
6. ✅ Monitor access logs

---

## Current Status

**Your VPS:**
- IP: `106.51.48.79`
- Port: `8080`
- Protocol: `HTTP` (not encrypted)

**Access:**
```bash
# From anywhere (not secure)
curl http://106.51.48.79:8080/health
```

**To make it secure:**
1. Get a domain name
2. Install Nginx + Let's Encrypt
3. Use HTTPS

---

## Summary

| Feature | HTTP (Current) | HTTPS (Recommended) |
|---------|----------------|---------------------|
| Encryption | ❌ No | ✅ Yes |
| Certificate | ❌ No | ✅ Yes |
| Secure | ❌ No | ✅ Yes |
| Cost | Free | Free (Let's Encrypt) |
| Setup Time | 0 min | 15 min |
| Production Ready | ❌ No | ✅ Yes |

**Bottom Line:**
- **Testing:** HTTP is fine (what you have now)
- **Production:** HTTPS is required (15-min setup)

---

## Next Steps

1. **For testing now:** Use HTTP - it works!
   ```bash
   curl http://106.51.48.79:8080/health
   ```

2. **For production later:** Set up HTTPS
   - Get domain name
   - Run the 15-minute setup above
   - Use `https://` instead of `http://`

**Your API works right now with HTTP - HTTPS is for production security!**

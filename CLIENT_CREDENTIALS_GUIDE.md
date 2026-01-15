# Client Access Guide - What to Share

## 🔑 What Clients Need

When a client wants to use your AI Gateway, you need to share **3 things**:

---

## 1. API Endpoint URL

**What to share:**
```
http://106.51.48.79:8080
```
or (if you set up HTTPS):
```
https://your-domain.com
```

**Example:**
```
Base URL: http://106.51.48.79:8080
```

---

## 2. Username & Password (for getting token)

**What to share:**
```
Username: client_username
Password: client_password
```

**Current default (CHANGE THIS!):**
```
Username: admin
Password: admin
```

⚠️ **You should create unique credentials for each client!**

---

## 3. API Documentation

**Share these files:**
- `CLIENT_API_GUIDE.md` - Simple guide with examples
- Or just the endpoint URLs and examples

---

## ❌ What NOT to Share

**NEVER share these:**
- ❌ JWT Secret Key (this stays on your server only)
- ❌ MongoDB credentials
- ❌ Server SSH access
- ❌ `.env` file
- ❌ Docker credentials

---

## 📝 Client Onboarding Template

### Email Template for New Clients

```
Subject: AI Gateway API Access

Hi [Client Name],

Here are your API credentials:

API Endpoint: http://106.51.48.79:8080
Username: [unique_username]
Password: [secure_password]

Documentation: [link to CLIENT_API_GUIDE.md]

Quick Start:
1. Get your token:
   curl -X POST "http://106.51.48.79:8080/auth/token" \
     -d "username=[username]&password=[password]"

2. Use the token for API calls:
   curl "http://106.51.48.79:8080/api/ocr" \
     -H "Authorization: Bearer YOUR_TOKEN"

Support: [your email]

Best regards,
[Your Name]
```

---

## 🔐 How Authentication Works

### Step 1: Client Gets Token
```bash
curl -X POST "http://106.51.48.79:8080/auth/token" \
  -d "username=client_user&password=client_pass"
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Step 2: Client Uses Token
```bash
curl "http://106.51.48.79:8080/api/ocr" \
  -H "Authorization: Bearer eyJhbGc..."
```

**The JWT secret is ONLY used by your server to sign/verify tokens - clients never see it!**

---

## 🔧 Creating Client Accounts

### Current Setup (Simple)

Right now, you have a **demo authentication** system with:
- Username: `admin`
- Password: `admin`

**For production, you need to:**

1. **Create a user database**
2. **Add user management endpoints**
3. **Generate unique credentials per client**

### Quick User Management (To Implement)

Add this to your gateway:

```python
# app/auth/users.py
users_db = {
    "client1": {
        "username": "client1",
        "password_hash": "hashed_password",
        "email": "client1@example.com",
        "active": True
    },
    "client2": {
        "username": "client2", 
        "password_hash": "hashed_password",
        "email": "client2@example.com",
        "active": True
    }
}
```

---

## 📊 What Each Client Needs

| Item | What to Share | Example |
|------|---------------|---------|
| **API URL** | ✅ Yes | `http://106.51.48.79:8080` |
| **Username** | ✅ Yes | `client_john` |
| **Password** | ✅ Yes | `SecurePass123!` |
| **Documentation** | ✅ Yes | `CLIENT_API_GUIDE.md` |
| **JWT Secret** | ❌ NO | (server only) |
| **MongoDB URI** | ❌ NO | (server only) |
| **Server Access** | ❌ NO | (admin only) |

---

## 🎯 Summary

### What Clients Get:
1. **API URL**: `http://106.51.48.79:8080`
2. **Username**: Unique per client
3. **Password**: Secure password
4. **Documentation**: CLIENT_API_GUIDE.md

### What Clients Do:
1. Get token using username/password
2. Use token for all API calls
3. Token expires after 60 minutes
4. Get new token when expired

### What You Keep Secret:
- JWT Secret (for signing tokens)
- MongoDB credentials
- Server access
- Other clients' credentials

---

## 🔒 Security Best Practices

1. **Unique credentials per client**
   - Don't share the same username/password
   
2. **Strong passwords**
   - At least 12 characters
   - Mix of letters, numbers, symbols

3. **HTTPS in production**
   - Encrypt all traffic
   - See SECURITY_GUIDE.md

4. **Monitor usage**
   - Track which client makes which requests
   - Use `X-Client-ID` header

5. **Revoke access**
   - Disable user accounts when needed
   - Change JWT secret to invalidate all tokens

---

## 📞 Client Support

### Common Client Questions

**Q: What is the JWT secret?**  
A: You don't need it! Just use your username/password to get a token.

**Q: My token expired, what do I do?**  
A: Get a new token using the `/auth/token` endpoint.

**Q: Can I share my credentials?**  
A: No! Each client should have unique credentials.

**Q: What's the rate limit?**  
A: 60 requests per minute per client.

---

## 🚀 Quick Reference

**For clients to start using your API:**

```bash
# 1. Get token
TOKEN=$(curl -s -X POST "http://106.51.48.79:8080/auth/token" \
  -d "username=YOUR_USERNAME&password=YOUR_PASSWORD" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Use API
curl "http://106.51.48.79:8080/health" \
  -H "Authorization: Bearer $TOKEN"
```

**That's it!** Clients never need to know about JWT secrets, MongoDB, or server internals.

# Backend EC2 Deployment Guide

## 1. AWS EC2 Security Group Configuration
In the AWS Management Console, navigate to your Backend EC2 Instance > **Security Groups** > **Edit Inbound Rules**, and add:

| Type | Protocol | Port Range | Source | Purpose |
|------|----------|------------|--------|---------|
| **SSH** | TCP | 22 | Your IP (or `0.0.0.0/0`) | Remote SSH terminal access |
| **Custom TCP** | TCP | 5000 | `0.0.0.0/0` (or Frontend EC2 IP) | Flask REST API & Health checks |

---

## 2. Quick Deploy (2 Commands)

Once uploaded to your backend EC2 instance, execute these 2 commands in terminal:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 3. How to Verify Live Backend

Run this verification command from your local terminal or EC2:

```bash
curl http://<YOUR_BACKEND_EC2_PUBLIC_IP>:5000/api/health
```

Expected JSON response:
```json
{
  "status": "healthy",
  "service": "Medicine Stock & Expiry Tracker Cloud Backend",
  "database": "SQLite (Dev Fallback)",
  "cors_origins": "*",
  "version": "2.0.0"
}
```

### Checking Logs
- If running Docker: `docker logs -f medstock-backend`
- If running Python: `cat backend.log`

# Frontend EC2 Deployment Guide

## 1. AWS EC2 Security Group Configuration
In the AWS Management Console, navigate to your Frontend EC2 Instance > **Security Groups** > **Edit Inbound Rules**, and add:

| Type | Protocol | Port Range | Source | Purpose |
|------|----------|------------|--------|---------|
| **SSH** | TCP | 22 | Your IP (or `0.0.0.0/0`) | Remote SSH terminal access |
| **HTTP** | TCP | 80 | `0.0.0.0/0` | Public browser access to React App |
| **HTTPS** (Optional) | TCP | 443 | `0.0.0.0/0` | SSL/TLS browser access |

---

## 2. Quick Deploy

### Step A: Set Execution Permissions
```bash
chmod +x deploy.sh
```

### Step B: Run the Deployment Script
You can pass the Backend EC2 Public IP directly as an argument:
```bash
./deploy.sh <YOUR_BACKEND_EC2_PUBLIC_IP>
```
*(Or run `./deploy.sh` without arguments and enter the Backend IP interactively when prompted).*

The script will automatically:
1. Configure `VITE_API_URL` pointing to `http://<YOUR_BACKEND_EC2_PUBLIC_IP>:5000/api`
2. Build the production React bundle
3. Start the Nginx container/service on port 80
4. Execute `curl -I http://localhost` to verify HTTP 200 OK

---

## 3. How to Verify Live Frontend

1. Open your web browser and navigate to:
   ```
   http://<YOUR_FRONTEND_EC2_PUBLIC_IP>
   ```
2. Verify that the UI loads and is able to connect to the backend (e.g. login with `admin@pharmacy.com` / `admin123` or view medicine inventory).

### Checking Logs
- If running Docker: `docker logs -f medstock-frontend`
- If running system Nginx: `sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log`

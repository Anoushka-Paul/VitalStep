# VitalStep API - Deployment Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Deployment Options](#deployment-options)
3. [Environment Setup](#environment-setup)
4. [Local Development](#local-development)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Supabase account
- HubSpot account with API access
- Docker (optional, for containerized deployment)

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd Multipatient-Vitalstep/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Run Locally
```bash
# Start the server
uvicorn app.main:app --reload --port 8000

# Or using Python
python app/main.py
```

Visit: http://localhost:8000/docs

---

## Deployment Options

### Option 1: Render (Recommended - Easiest)

**Why Render?**
- Free tier available
- Auto-deploy from Git
- Built-in SSL
- Easy environment variable management
- Docker support

**Steps:**

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Deploy to Render"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

3. **Deploy**
   - Click "New +" → "Blueprint"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml`
   - Click "Apply"

4. **Set Environment Variables**
   In Render dashboard, go to your service → Environment:
   ```env
   SUPABASE_ANON_KEY=your_key_here
   HUBSPOT_PAT=your_token_here
   SECRET_KEY=generate_random_string
   CORS_ORIGINS=https://your-app.com
   ```

5. **Deploy**
   - Render will build and deploy automatically
   - Your API will be live at: `https://vitalstep-api.onrender.com`

**Cost:** Free tier available, $7/month for starter plan

---

### Option 2: Railway

**Steps:**

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Initialize Project**
   ```bash
   railway init
   railway link
   ```

3. **Deploy**
   ```bash
   railway up
   ```

4. **Set Variables**
   ```bash
   railway variables set SUPABASE_ANON_KEY=your_key
   railway variables set HUBSPOT_PAT=your_token
   ```

**Cost:** $5/month hobby plan

---

### Option 3: Fly.io (Best Performance)

**Steps:**

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Launch App**
   ```bash
   fly launch
   # Follow prompts
   ```

3. **Set Secrets**
   ```bash
   fly secrets set SUPABASE_ANON_KEY=your_key
   fly secrets set HUBSPOT_PAT=your_token
   ```

4. **Deploy**
   ```bash
   fly deploy
   ```

**Cost:** ~$5/month with free tier

---

### Option 4: Docker (Any VPS)

**Steps:**

1. **Build Image**
   ```bash
   docker build -t vitalstep-api ./backend
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name vitalstep-api \
     -p 8000:8000 \
     -e SUPABASE_URL=https://your-project.supabase.co \
     -e SUPABASE_ANON_KEY=your_key \
     -e HUBSPOT_PAT=your_token \
     -e ENVIRONMENT=production \
     vitalstep-api
   ```

3. **Or use Docker Compose**
   ```bash
   docker-compose up -d
   ```

**VPS Options:**
- DigitalOcean: $4/month droplet
- Linode: $5/month
- AWS EC2: Free tier available

---

## Environment Setup

### Required Environment Variables

Create `.env` file in backend directory:

```env
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_PREFIX=/api/v1
SECRET_KEY=your_secure_secret_key_here

# Supabase (Primary Database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here

# Supabase (Secondary Database - Optional)
SUPABASE_URL_2=https://your-second-project.supabase.co
SUPABASE_ANON_KEY_2=your_second_anon_key

# HubSpot
HUBSPOT_PAT=your_hubspot_personal_access_token

# ML Model
MODEL_PATH=../ml/artifacts
MODEL_VERSION=latest

# CORS (comma-separated for production)
CORS_ORIGINS=https://your-app.com,https://www.your-app.com
```

### Getting Credentials

**Supabase:**
1. Go to https://supabase.com
2. Create project
3. Settings → API → Copy URL and anon key

**HubSpot:**
1. Go to https://hubspot.com
2. Settings → Integrations → API Key
3. Create private app with required scopes:
   - `crm.objects.contacts.write`
   - `crm.objects.contacts.read`
   - `crm.schemas.contacts.write`

---

## Local Development

### Using Virtual Environment
```bash
cd backend

# Create venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000

# Or with Python
python app/main.py
```

### Using Docker Compose
```bash
# Start all services
docker-compose up

# With Redis cache
docker-compose --profile with-cache up

# Stop services
docker-compose down
```

### Testing
```bash
# Run phone normalization tests
python test_phone_normalization.py

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/ml/health
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set strong `SECRET_KEY`
- [ ] Verify Supabase credentials
- [ ] Verify HubSpot PAT
- [ ] Test health endpoints
- [ ] Enable HTTPS (automatic on most platforms)
- [ ] Set up monitoring (optional)

### Deploy to Render (Step-by-Step)

1. **Prepare Repository**
   ```bash
   git add .
   git commit -m "Prepare for production"
   git push origin main
   ```

2. **Create Render Service**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect GitHub repo
   - Select repository
   - Render detects `render.yaml`

3. **Configure Environment**
   In Render dashboard:
   - Go to your service
   - Click "Environment"
   - Add these variables:
     ```
     SUPABASE_ANON_KEY = your_key
     HUBSPOT_PAT = your_token
     SECRET_KEY = random_string_here
     CORS_ORIGINS = https://your-app.com
     ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (~2-3 minutes)
   - Your API is live!

5. **Test Deployment**
   ```bash
   # Health check
   curl https://vitalstep-api.onrender.com/health
   
   # API docs
   # Visit: https://vitalstep-api.onrender.com/docs
   ```

### Custom Domain (Optional)

1. In Render dashboard, go to your service
2. Click "Settings" → "Custom Domains"
3. Add your domain
4. Update DNS records as instructed
5. SSL certificate auto-provisioned

---

## Monitoring & Maintenance

### Health Checks

**Endpoints:**
- `GET /health` - Overall health
- `GET /health/ready` - Readiness probe (Kubernetes)
- `GET /health/live` - Liveness probe (Kubernetes)

**Monitor:**
- Database connectivity
- ML model status
- HubSpot API status
- Response times

### Logs

**Render:**
```bash
# View logs in dashboard
# Or use CLI
render logs -f vitalstep-api
```

**Docker:**
```bash
docker logs -f vitalstep-api
```

### Scaling

**Render:**
- Upgrade plan (Starter → Standard → Pro)
- Increase `numInstances` in render.yaml
- Add Redis for caching

**Performance Tips:**
1. Enable GZip compression (already enabled)
2. Use Redis for frequent queries
3. Cache ML predictions
4. Use CDN for static assets
5. Optimize database queries

### Updates

**Automatic (Render):**
- Push to main branch → auto-deploy

**Manual:**
```bash
# Render CLI
render deploy

# Docker
docker-compose pull
docker-compose up -d
```

### Backup

**Supabase:**
- Automatic backups in Supabase dashboard
- Export data regularly

**ML Models:**
- Backup `ml/artifacts/` directory
- Version control model files

---

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
```
Error: Failed to initialize database connections
```
**Solution:** Check SUPABASE_URL and SUPABASE_ANON_KEY in environment variables

**2. HubSpot API Errors**
```
Error: HubSpot sync failed
```
**Solution:** Verify HUBSPOT_PAT has correct permissions

**3. ML Model Not Loading**
```
Warning: Model file not found
```
**Solution:** Ensure `ml/artifacts/quantile_model_enhanced.pkl` exists

**4. CORS Errors**
```
Access-Control-Allow-Origin error
```
**Solution:** Update CORS_ORIGINS in environment variables

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Support

- Check logs first
- Review API docs at `/docs`
- Test endpoints individually
- Verify environment variables

---

## API Documentation

Once deployed, visit:
- **Swagger UI:** `https://your-api.com/docs`
- **ReDoc:** `https://your-api.com/redoc`

### Key Endpoints

**ML Predictions:**
- `POST /api/v1/ml/predict` - Single prediction
- `POST /api/v1/ml/predict/batch` - Batch predictions
- `GET /api/v1/ml/model/info` - Model information

**HubSpot Sync:**
- `POST /api/v1/hubspot/sync/contact` - Sync single contact
- `POST /api/v1/hubspot/sync/batch` - Batch sync
- `GET /api/v1/hubspot/health` - HubSpot status

**Patients:**
- `GET /api/v1/patients/` - List patients
- `POST /api/v1/patients/` - Create patient
- `GET /api/v1/patients/{id}/readings` - Get readings

---

## Security

### Production Security Checklist

- [ ] Use HTTPS only
- [ ] Set strong SECRET_KEY
- [ ] Configure CORS properly (no `*` in production)
- [ ] Enable rate limiting (if needed)
- [ ] Regular security updates
- [ ] Monitor API usage
- [ ] Rotate API keys periodically
- [ ] Use environment variables (never hardcode)
- [ ] Enable logging and monitoring

### Rate Limiting

Add to `app/main.py` if needed:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## Cost Estimation

### Render (Production)
- Starter Plan: $7/month
- Disk (1GB): $0.10/month
- **Total: ~$7-10/month**

### Railway
- Hobby Plan: $5/month
- **Total: ~$5-10/month**

### Fly.io
- Shared CPU: ~$5/month
- **Total: ~$5-10/month**

### VPS (DigitalOcean)
- Droplet: $4/month
- **Total: ~$4-6/month**

---

## Next Steps

1. ✅ Deploy API
2. ✅ Test all endpoints
3. ✅ Set up monitoring
4. ✅ Configure custom domain
5. ✅ Update Flutter app to use API
6. ✅ Set up CI/CD
7. ✅ Add analytics
8. ✅ Scale as needed

---

## Questions?

Check the main README.md or create an issue in the repository.
# VitalStep - Deployment Guide

## 🎯 Quick Overview

**Your Current Setup:**
- ✅ **Database:** Supabase (already set up at https://cbebmpgsbxqdzpfgqulj.supabase.co)
- ✅ **HubSpot:** Connected and syncing
- ✅ **Backend Code:** Ready to deploy
- ⏳ **Backend Hosting:** Not deployed yet

**What you need:**
1. Deploy the FastAPI backend to a hosting service
2. Connect it to your Supabase database
3. Update your Flutter app to use the deployed API

---

## 🚀 Step 1: Deploy Backend API

### Option A: Render (RECOMMENDED - Easiest)

**Why Render?**
- ✅ Already configured (`render.yaml` exists)
- ✅ Free tier available ($7/month for production)
- ✅ Auto-deploy from GitHub
- ✅ Built-in SSL
- ✅ Easy environment variable management

**Steps:**

1. **Push code to GitHub** (if not already done)
   ```bash
   cd c:/Users/anous/Desktop/VitalStep/Multipatient-Vitalstep
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up with your GitHub account

3. **Deploy Backend**
   - Click **"New +"** → **"Blueprint"**
   - Connect your GitHub repository: `Anoushka-Paul/VitalStep`
   - Render will auto-detect `render.yaml` file
   - Click **"Apply"**

4. **Set Environment Variables**
   
   In Render dashboard, go to your service → **Environment** tab:
   
   ```env
   # Required
   SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (your key from Supabase)
   HUBSPOT_PAT = your_hubspot_personal_access_token
   SECRET_KEY = generate_random_string_here (use any random string)
   
   # Optional (defaults are fine)
   ENVIRONMENT = production
   LOG_LEVEL = INFO
   API_PREFIX = /api/v1
   CORS_ORIGINS = https://your-flutter-app.com
   ```

5. **Deploy**
   - Click **"Create Web Service"**
   - Wait 2-3 minutes for build
   - Your API will be live at: `https://vitalstep-api.onrender.com`

6. **Test Deployment**
   ```bash
   # Health check
   curl https://vitalstep-api.onrender.com/health
   
   # API docs
   # Visit: https://vitalstep-api.onrender.com/docs
   ```

---

### Option B: Railway (Alternative)

**Cost:** $5/month

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Deploy**
   ```bash
   cd backend
   railway init
   railway link
   railway up
   ```

3. **Set Variables**
   ```bash
   railway variables set SUPABASE_ANON_KEY=your_key
   railway variables set HUBSPOT_PAT=your_token
   railway variables set SECRET_KEY=random_string
   ```

---

### Option C: Supabase Edge Functions (FREE - Limited)

**Note:** This is NOT your Supabase database, but Supabase's hosting service for serverless functions.

**Pros:**
- ✅ Free (500k requests/month)
- ✅ Same platform as your database
- ✅ Easy deployment

**Cons:**
- ⚠️ Limited to 500k requests/month
- ⚠️ Cold starts (slower first request)
- ⚠️ Max 10MB function size

**Steps:**

1. **Install Supabase CLI**
   ```bash
   npm i -g @supabase/cli
   supabase login
   ```

2. **Create Edge Function**
   ```bash
   cd c:/Users/anous/Desktop/VitalStep/Multipatient-Vitalstep
   supabase functions deploy api --project-ref cbebmpgsbxqdzpfgqulj
   ```

3. **Set Secrets**
   ```bash
   supabase secrets set SUPABASE_ANON_KEY=your_key --project-ref cbebmpgsbxqdzpfgqulj
   supabase secrets set HUBSPOT_PAT=your_token --project-ref cbebmpgsbxqdzpfgqulj
   ```

4. **Your API will be at:**
   ```
   https://cbebmpgsbxqdzpfgqulj.supabase.co/functions/v1/api
   ```

---

## 📱 Step 2: Update Flutter App

After deploying your backend, update your Flutter app to use the new API:

1. **Find your API URL:**
   - Render: `https://vitalstep-api.onrender.com`
   - Railway: `https://your-app.up.railway.app`
   - Supabase: `https://cbebmpgsbxqdzpfgqulj.supabase.co/functions/v1/api`

2. **Update Flutter Configuration**

   In your Flutter app, update the API base URL:
   
   ```dart
   // lib/services/api_service.dart or similar
   const String API_BASE_URL = 'https://vitalstep-api.onrender.com';
   ```

3. **Test Connection**
   ```bash
   flutter run --dart-define=API_BASE_URL=https://vitalstep-api.onrender.com
   ```

---

## ✅ Deployment Checklist

### Before Deployment:
- [x] Supabase database is set up
- [x] HubSpot integration is working
- [x] Backend code is complete
- [ ] Code pushed to GitHub
- [ ] Choose hosting platform (Render recommended)
- [ ] Create hosting account
- [ ] Set environment variables
- [ ] Deploy backend
- [ ] Test health endpoint
- [ ] Update Flutter app with API URL
- [ ] Test Flutter app connection

---

## 🔧 Troubleshooting

### Issue: "Database connection failed"
**Solution:** Check `SUPABASE_ANON_KEY` in environment variables

### Issue: "HubSpot sync failed"
**Solution:** Verify `HUBSPOT_PAT` has correct permissions

### Issue: "CORS errors"
**Solution:** Update `CORS_ORIGINS` with your Flutter app domain

### Issue: "Build failed on Render"
**Solution:** Check logs in Render dashboard, ensure `requirements.txt` is complete

---

## 📊 Post-Deployment

### Monitor Your API:
1. **Render Dashboard:**
   - View logs
   - Check metrics
   - Monitor errors

2. **Health Checks:**
   ```bash
   # Overall health
   curl https://your-api.com/health
   
   # Readiness check
   curl https://your-api.com/health/ready
   ```

3. **API Documentation:**
   - Visit: `https://your-api.com/docs`
   - Test endpoints interactively

---

## 🎯 Next Steps After Deployment

1. **Test Patient Creation:**
   - Create a test patient via API
   - Verify it syncs to HubSpot
   - Check device_id is set correctly

2. **Test Condition Field:**
   - Create patient with condition field
   - Verify it syncs to HubSpot

3. **Update Flutter App:**
   - Point to production API
   - Test all features
   - Submit to app stores

---

## 💡 Recommendations

**For Production:**
- Use **Render** (already configured, reliable)
- Upgrade to Starter plan ($7/month)
- Set up custom domain
- Enable monitoring

**For Testing/MVP:**
- Use **Supabase Edge Functions** (free)
- Good for testing before paying
- Limited to 500k requests/month

---

## 📞 Support

If you need help:
1. Check the logs in your hosting dashboard
2. Visit API docs at `/docs`
3. Review `backend/DEPLOYMENT.md` for more details

---

**Ready to deploy?** Follow Option A (Render) for easiest setup! 🚀
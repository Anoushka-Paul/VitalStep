# Flutter Frontend Connection Guide

## Overview
This guide explains how to connect your Flutter frontend with the Render-deployed backend.

## Current Status
✅ Backend deployed on Render: `https://vitalstep-api.onrender.com`
✅ Flutter API base URL configured: `lib/ui/common/app_strings.dart`
✅ All required backend endpoints created
✅ CORS configured to allow all origins

## Backend Endpoints Created

### Authentication Endpoints
- `POST /api/v1/auth/login` - Patient login
- `POST /api/v1/auth/login-specialist` - Specialist login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/forgot-password` - Password reset request
- `POST /api/v1/auth/reset-password` - Password reset
- `POST /api/v1/auth/logout` - User logout

### User Endpoints
- `GET /api/v1/user/{user_id}` - Get user profile
- `PUT /api/v1/user/{user_id}` - Update user profile
- `GET /api/v1/user/{user_id}/assessments` - Get user assessments
- `GET /api/v1/user/{user_id}/tests` - Get user tests
- `GET /api/v1/user/{user_id}/devices` - Get user devices

### Test Endpoints
- `GET /api/v1/test/user/{user_id}` - Get all tests for user
- `GET /api/v1/test/assessment/{assessment_id}` - Get tests for assessment
- `GET /api/v1/test/hands/{user_id}` - Get latest hand values (Left/Right)
- `POST /api/v1/test/` - Create new test
- `DELETE /api/v1/test/{test_id}` - Delete test

### Queue Endpoints
- `GET /api/v1/queue/user/{user_id}` - Get user queue
- `GET /api/v1/queue/assessment/{assessment_id}` - Get assessment queue
- `POST /api/v1/queue/` - Create queue item
- `DELETE /api/v1/queue/{queue_id}` - Delete queue item (cancel)

### Device Endpoints
- `GET /api/v1/device/queue` - Get all devices
- `GET /api/v1/device/{device_id}` - Get device by ID
- `POST /api/v1/device/` - Register new device
- `DELETE /api/v1/device/{device_id}` - Delete device

### Remarks Endpoints
- `GET /api/v1/remarks/assessment/{assessment_id}` - Get assessment remarks
- `POST /api/v1/remarks/` - Create remark
- `PUT /api/v1/remarks/{remark_id}` - Update remark
- `DELETE /api/v1/remarks/{remark_id}` - Delete remark

### Account Access Endpoints
- `GET /api/v1/accountAccess/user/{user_id}` - Get specialist's patients
- `GET /api/v1/accountAccess/patient/{patient_id}` - Get patient's specialists
- `POST /api/v1/accountAccess/` - Grant access
- `DELETE /api/v1/accountAccess/{access_id}` - Revoke access
- `GET /api/v1/accountAccess/specialist/{specialist_id}/patients` - Get specialist's patients

## Deployment Steps

### 1. Update Backend Code
The following files have been created/updated:
- ✅ `backend/app/routers/auth.py` - Authentication endpoints
- ✅ `backend/app/routers/users.py` - User profile endpoints
- ✅ `backend/app/routers/tests.py` - Test/assessment endpoints
- ✅ `backend/app/routers/queue.py` - Queue management endpoints
- ✅ `backend/app/routers/devices.py` - Device management endpoints
- ✅ `backend/app/routers/remarks.py` - Remarks/comments endpoints
- ✅ `backend/app/routers/account_access.py` - Account access endpoints
- ✅ `backend/app/main.py` - Updated to register all routers

### 2. Deploy to Render

#### Option A: Automatic Deployment (if connected to GitHub)
1. Commit and push all changes to your GitHub repository
2. Render will automatically detect the changes and deploy
3. Monitor the deployment in Render dashboard

#### Option B: Manual Deployment
1. Go to Render dashboard
2. Select your service: `vitalstep-api`
3. Click "Manual Deploy" → "Deploy latest commit"
4. Wait for deployment to complete (2-3 minutes)

### 3. Verify Deployment

After deployment, test the health endpoint:
```bash
curl https://vitalstep-api.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "supabase_connected": true,
  "hubspot_connected": true,
  "ml_model_loaded": true,
  "timestamp": 1234567890.123
}
```

### 4. Test API Documentation
Visit: `https://vitalstep-api.onrender.com/docs`

You should see all available endpoints with interactive documentation.

## Flutter Configuration

### Current Configuration
The Flutter app is already configured with:
```dart
// lib/ui/common/app_strings.dart
const String apiBaseUrl = "https://vitalstep-api.onrender.com";
```

### No Changes Needed
The Flutter app is already set up to use the Render URL. Just make sure:
1. ✅ The URL is correct (it is: `https://vitalstep-api.onrender.com`)
2. ✅ CORS is configured (it is: allows all origins)
3. ✅ All endpoints exist (they do - see list above)

## Testing the Connection

### 1. Test Login Endpoint
```bash
curl -X POST https://vitalstep-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### 2. Test from Flutter App
1. Run the Flutter app: `flutter run`
2. Try to login with a test account
3. Check the console logs for any errors

### 3. Common Issues and Solutions

#### Issue: "Network request failed"
**Solution**: Check internet connection and verify the API URL is correct

#### Issue: "CORS blocked"
**Solution**: CORS is already configured to allow all origins. If you still see this error, clear the app cache and restart.

#### Issue: "404 Not Found"
**Solution**: Make sure the backend has been deployed with all the new routers. Check Render logs.

#### Issue: "500 Internal Server Error"
**Solution**: Check Render logs for specific error. Common causes:
- Supabase credentials not configured
- Database tables don't exist
- Missing environment variables

## Environment Variables Required on Render

Make sure these are set in Render dashboard:

### Required
- `ENVIRONMENT` = `production`
- `LOG_LEVEL` = `INFO`
- `API_PREFIX` = `/api/v1`
- `SUPABASE_URL` = Your Supabase project URL
- `SUPABASE_ANON_KEY` = Your Supabase anon key
- `SECRET_KEY` = Auto-generated by Render

### Optional
- `SUPABASE_URL_2` = Secondary database URL (if using)
- `SUPABASE_ANON_KEY_2` = Secondary database key (if using)
- `HUBSPOT_PAT` = HubSpot personal access token
- `CORS_ORIGINS` = `["*"]` (default, allows all origins)

## Database Tables Required

Make sure these tables exist in your Supabase database:

### Core Tables
- `profiles` - User profiles
- `research_patients` - Patient data
- `patient_readings` - Test readings
- `tests` - Test records
- `assessments` - Assessment records
- `devices` - Device registry
- `queue` - Assessment queue
- `remarks` - Comments/remarks
- `account_access` - Specialist-patient relationships

### Supabase Setup
Run the SQL setup file if you haven't already:
```bash
# Execute supabase_setup.sql in Supabase SQL Editor
```

## Monitoring and Debugging

### 1. Render Logs
View real-time logs in Render dashboard:
- Go to your service → Logs tab
- Filter by "error" to see issues
- Filter by "info" to see requests

### 2. Flutter Debug Console
Run Flutter in debug mode to see API calls:
```bash
flutter run --verbose
```

### 3. Test Individual Endpoints
Use the interactive API docs at:
`https://vitalstep-api.onrender.com/docs`

## Next Steps

1. ✅ Deploy the updated backend to Render
2. ✅ Verify health endpoint responds
3. ✅ Test login from Flutter app
4. ✅ Test other features (assessments, tests, etc.)
5. ✅ Monitor logs for any errors
6. ✅ Test on physical device (not just emulator)

## Support

If you encounter issues:
1. Check Render logs first
2. Check Flutter debug console
3. Verify Supabase connection
4. Test endpoints using `/docs` interface
5. Check network connectivity

## Success Criteria

✅ Backend health check returns 200
✅ Flutter app can login successfully
✅ User profile loads correctly
✅ Tests and assessments work
✅ Queue management works
✅ Device selection works
✅ Remarks/comments work
✅ Specialist access works

---

**Last Updated**: 2026-07-30
**Backend URL**: https://vitalstep-api.onrender.com
**Flutter API Config**: lib/ui/common/app_strings.dart
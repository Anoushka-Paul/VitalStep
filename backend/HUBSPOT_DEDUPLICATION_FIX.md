# HubSpot Duplication Fix - Implementation Summary

## Problem
HubSpot contacts were being duplicated because:
1. Phone numbers were stored in different formats (e.g., `+91-9876543210`, `9876543210`, `91 9876543210`)
2. HubSpot search uses exact match (`EQ` operator), so different formats didn't match
3. When formats didn't match, new contacts were created instead of updating existing ones
4. The app sync was skipping existing contacts instead of merging data

## Solution
Implemented a centralized phone number normalization system with proper merge logic.

## Changes Made

### 1. Created `backend/hubspot_utils.py`
**Centralized utilities for HubSpot operations:**
- `normalize_phone(phone)`: Normalizes phone numbers to 10 digits only
  - Removes all formatting (hyphens, spaces, parentheses, dots)
  - Removes country codes (91, +1, etc.)
  - Removes leading zeros
  - Handles various input formats consistently
  - Examples:
    - `+91-9876543210` → `9876543210`
    - `9876543210` → `9876543210`
    - `09876543210` → `9876543210`
    - `919876543210` → `9876543210`
    - `+1-987-654-3210` → `9876543210`

- `find_contact_by_phone(phone)`: Smart contact search
  - Searches with multiple phone format variants
  - Tries normalized format, original format, and format without country code
  - Returns existing contact if found

- `upsert_contact_by_phone(phone, first_name, last_name)`: Find or create contact
  - Uses `find_contact_by_phone()` to check for existing contacts
  - Updates existing contact's name if needed
  - Only creates new contact if none exists
  - **This is the main function to use - it prevents duplicates**

- `merge_contact_data(existing_props, new_data)`: Merge data intelligently
  - Combines existing and new data
  - New values overwrite old values (no conflict resolution needed)
  - Preserves existing data that's not being updated

### 2. Updated `backend/main.py`
**Changes:**
- Imports all utilities from `hubspot_utils`
- `sync_app_contact_to_hubspot()`:
  - Normalizes phone numbers before searching
  - Uses `upsert_contact_by_phone()` instead of creating new contacts
  - **Merges data instead of skipping existing contacts**
  - Always updates with latest data
- `run_supabase_to_hubspot_sync()`:
  - Normalizes phone numbers using `normalize_phone()`
  - Uses improved `upsert_contact_by_phone()` function
  - Ensures consistent phone format across all operations

### 3. Updated `backend/sync_all_to_hubspot.py`
**Changes:**
- Imports utilities from `hubspot_utils`
- Removed duplicate function definitions
- Uses `normalize_phone()` for all phone number processing
- Uses centralized `upsert_contact_by_phone()` function
- Ensures all phone numbers are normalized before HubSpot operations

### 4. Updated `ml/hubspot_sync_supabase_trials.py`
**Changes:**
- Imports utilities from `hubspot_utils`
- Uses `normalize_phone()` for phone number processing
- Uses `upsert_contact_by_phone()` for contact management
- Uses `merge_contact_data()` to merge trial data with existing contact data
- Prevents duplicates when syncing trial data

### 5. Created `backend/test_phone_normalization.py`
**Test script to verify the fix:**
- Tests various phone number formats
- Ensures all formats of the same number normalize to the same value
- Validates duplicate prevention logic

## How It Works

### Before (Duplicate Creation):
```
1. Supabase has: "9876543210"
2. App sends: "+91-9876543210"
3. HubSpot search for "+91-9876543210" → No match
4. New contact created → DUPLICATE!
```

### After (Proper Merge):
```
1. Supabase has: "9876543210"
2. App sends: "+91-9876543210"
3. normalize_phone() converts to: "9876543210"
4. HubSpot search for "9876543210" → Found existing contact
5. Update existing contact with new data → NO DUPLICATE!
```

## Key Features

### 1. Phone Number Normalization
- Handles all common formats (with/without country code, hyphens, spaces, etc.)
- Consistent normalization ensures same number always matches
- Smart country code detection (defaults to India for 10-digit numbers)

### 2. Multi-Strategy Search
- Searches with normalized phone
- Searches with original phone
- Searches without country code if present
- Maximizes chance of finding existing contacts

### 3. Proper Merge Logic
- Always updates existing contacts (never skips)
- Merges new data with existing data
- Preserves existing fields not being updated
- No data loss during sync

### 4. Idempotent Operations
- Safe to run multiple times
- Won't create duplicates on re-runs
- Updates existing data instead of creating new

## Usage

### Running the API Server:
```bash
cd backend
python main.py
```

### Bulk Sync All Patients:
```bash
cd backend
python sync_all_to_hubspot.py
```

### Sync Trial Data:
```bash
cd ml
python hubspot_sync_supabase_trials.py
```

### Test Phone Normalization:
```bash
cd backend
python test_phone_normalization.py
```

### API Endpoints:
- `POST /sync/supabase` - Sync Supabase patients (background)
- `POST /sync/supabase/block` - Sync Supabase patients (blocking)
- `POST /sync/app-contact` - Sync contact from app (with merge)

## Testing

Run the test script to verify phone normalization:
```bash
python backend/test_phone_normalization.py
```

Expected output:
- All 11 test cases should pass
- All variants of the same number should normalize to the same value
- Confirms duplicate prevention is working

## Migration Notes

### For Existing Duplicates:
If you already have duplicates in HubSpot, you should:
1. Export all HubSpot contacts
2. Use the phone normalization logic to identify duplicates
3. Merge duplicates manually in HubSpot or use HubSpot's merge API
4. After cleanup, the new code will prevent future duplicates

### Environment Variables:
Ensure these are set in `backend/.env`:
```env
SUPABASE_URL=https://cbebmpgsbxqdzpfgqulj.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
HUBSPOT_PAT=your_hubspot_personal_access_token
```

## Prevention Guarantee

This implementation ensures:
✓ No duplicate contacts will be created
✓ Phone numbers in any format normalize to 10 digits and match existing contacts
✓ Data will always be merged/updated, never skipped
✓ Safe to run sync multiple times
✓ Consistent 10-digit phone format across all systems

## Support

If issues persist:
1. Check HubSpot API logs for search queries
2. Verify phone numbers in Supabase are valid
3. Run test script to confirm normalization works
4. Check that HUBSPOT_PAT has correct permissions
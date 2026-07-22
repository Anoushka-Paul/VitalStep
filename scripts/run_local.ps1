# Load .env into environment variables and run the HubSpot sync script
$envFile = Join-Path $PSScriptRoot "..\.env"
if (-Not (Test-Path $envFile)) {
  Write-Host ".env not found at $envFile. Create one from .env.example and add HUBSPOT_PAT." -ForegroundColor Yellow
  exit 1
}
Get-Content $envFile | ForEach-Object {
  if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
    $name = $matches[1].Trim()
    $value = $matches[2].Trim()
    # Use Set-Item to write to the environment provider
    Set-Item -Path "Env:\$name" -Value $value -Force
  }
}

Push-Location (Join-Path $PSScriptRoot "..")
python ml/hubspot_sync_supabase_trials.py
Pop-Location

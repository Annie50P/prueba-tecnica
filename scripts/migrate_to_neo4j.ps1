# Migration to Neo4j + Graphiti
# Run as: powershell -ExecutionPolicy Bypass -File scripts/migrate_to_neo4j.ps1

Write-Host "=========================================="
Write-Host "MIGRATION TO NEO4J + GRAPHITI"
Write-Host "=========================================="
Write-Host ""

# 1. Verify Docker
Write-Host "[1/7] Verifying Docker..."
$dockerStatus = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker is not running"
    Write-Host "Please start Docker Desktop"
    exit 1
}
Write-Host "[OK] Docker running"

# 2. Clean containers
Write-Host ""
Write-Host "[2/7] Cleaning containers..."
docker compose down 2>$null
docker compose rm -f 2>$null
Write-Host "[OK] Containers cleaned"

# 3. Pull images if needed
Write-Host ""
Write-Host "[3/7] Checking images..."
docker pull neo4j:5.22.0 2>$null
docker pull zepai/graphiti:latest 2>$null
Write-Host "[OK] Images ready"

# 4. Build and up
Write-Host ""
Write-Host "[4/7] Building..."
docker compose build --no-cache

Write-Host ""
Write-Host "[5/7] Starting services..."
docker compose up -d

# 5. Wait for Neo4j
Write-Host ""
Write-Host "[6/7] Waiting for Neo4j..."
$maxAttempts = 30
for ($i = 1; $i -le $maxAttempts; $i++) {
    $neo4jTest = docker exec neo4j cypher-shell -u neo4j -p password123 "RETURN 1" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Neo4j ready"
        break
    }
    Write-Host "   Waiting... ($i/$maxAttempts)"
    Start-Sleep -Seconds 2
}

# 6. Wait for Graphiti
Write-Host ""
Write-Host "[7/7] Waiting for Graphiti..."
for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($health.StatusCode -eq 200) {
            Write-Host "[OK] Graphiti ready"
            break
        }
    } catch {}
    Write-Host "   Waiting... ($i/$maxAttempts)"
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "=========================================="
Write-Host "MIGRATION COMPLETE"
Write-Host "=========================================="
Write-Host ""
Write-Host "Verify at:"
Write-Host "  - Neo4j Browser: http://localhost:7474"
Write-Host "  - Graphiti: http://localhost:8000"
Write-Host "  - API: http://localhost:8001"
Write-Host ""
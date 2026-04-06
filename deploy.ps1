# deploy.ps1
Write-Host "Deploying AI PDF Pipeline via Docker Windows CLI..." -ForegroundColor Green

# 1. 기존 동작중인 로컬 컨테이너 중지 및 삭제 (ErrorAction=SilentlyContinue로 없는 컨테이너 에러 무시)
Write-Host "Stopping and removing existing containers..."
$existing_container = docker ps -a -q -f name="pdf_pipeline_container"
if ($existing_container) {
    docker stop pdf_pipeline_container
    docker rm pdf_pipeline_container
}

# 2. 새로운 Docker 이미지 빌드
Write-Host "Building Docker Image..." -ForegroundColor Yellow
docker build -t pdf_pipeline_image .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed. Deployment aborted." -ForegroundColor Red
    exit 1
}

# 3. 새로운 컨테이너 백그라운드 실행
Write-Host "Starting new container..." -ForegroundColor Yellow
docker run -d --restart unless-stopped --name pdf_pipeline_container -p 8000:8000 pdf_pipeline_image

Write-Host "Deployment Complete! Server is alive at http://localhost:8000" -ForegroundColor Cyan

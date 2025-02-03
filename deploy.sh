set +ex

docker build -t gcr.io/premium-state-449406-n8/planet-demo:v1 -f docker/Dockerfile .
docker push gcr.io/premium-state-449406-n8/planet-demo:v1

gcloud run deploy planet-stanford \
    --image gcr.io/premium-state-449406-n8/planet-demo:v1 \
    --platform managed \
    --region us-east1 \
    --allow-unauthenticated  # Or use service account if not public
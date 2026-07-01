#!/bin/bash
# PulseBoard Google Cloud Run Deployment Script
# Make sure to run 'gcloud auth login' and set your active project before running.

set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="pulseboard"
REGION="us-central1"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
SCHEDULER_JOB_NAME="pulseboard-daily-trigger"
SCHEDULE="0 9 * * 1-5" # Runs daily at 9:00 AM (Monday to Friday)

echo "============================================="
echo "Deploying PulseBoard to Google Cloud Run"
echo "Project ID: ${PROJECT_ID}"
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "============================================="

# 1. Build the Docker container using Cloud Build
echo "Building container image using Cloud Build..."
gcloud builds submit --tag "${IMAGE_TAG}" --project "${PROJECT_ID}" .

# 2. Deploy the container to Cloud Run
echo "Deploying container to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_TAG}" \
    --region "${REGION}" \
    --platform managed \
    --no-allow-unauthenticated \
    --set-env-vars="GEMINI_API_KEY=your_key_here" \
    --project "${PROJECT_ID}"

# Retrieve Cloud Run Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')
echo "Cloud Run Service deployed successfully!"
echo "Service URL: ${SERVICE_URL}"

# 3. Setup service account for Scheduler invocation
echo "Configuring Service Account and IAM roles for Cloud Scheduler..."
SERVICE_ACCOUNT_NAME="pulseboard-scheduler-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create Service Account if not exists
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" &>/dev/null; then
    gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --display-name="PulseBoard Cloud Scheduler Service Account"
fi

# Grant Cloud Run Invoker role to the Service Account
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.invoker" \
    --project "${PROJECT_ID}"

# 4. Create Cloud Scheduler Job
echo "Creating/Updating Cloud Scheduler job..."
if gcloud scheduler jobs describe "${SCHEDULER_JOB_NAME}" --location="${REGION}" &>/dev/null; then
    # Update existing job
    gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
        --location="${REGION}" \
        --schedule="${SCHEDULE}" \
        --uri="${SERVICE_URL}" \
        --http-method=POST \
        --oidc-service-account-email="${SERVICE_ACCOUNT_EMAIL}" \
        --project "${PROJECT_ID}"
else
    # Create new job
    gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
        --location="${REGION}" \
        --schedule="${SCHEDULE}" \
        --uri="${SERVICE_URL}" \
        --http-method=POST \
        --oidc-service-account-email="${SERVICE_ACCOUNT_EMAIL}" \
        --project "${PROJECT_ID}"
fi

echo "============================================="
echo "Deployment and Schedule creation complete!"
echo "PulseBoard will run on scheduler trigger: '${SCHEDULE}'"
echo "============================================="

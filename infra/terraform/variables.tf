variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "api_service_name" {
  description = "Cloud Run service name for the API"
  type        = string
  default     = "clearview-api"
}

variable "worker_service_name" {
  description = "Cloud Run service name for the worker"
  type        = string
  default     = "clearview-worker"
}

variable "api_image" {
  description = "Container image for the API service"
  type        = string
}

variable "worker_image" {
  description = "Container image for the worker service"
  type        = string
}

variable "db_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "clearview-db"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "ai_email_app"
}

variable "db_user" {
  description = "Database user name"
  type        = string
  default     = "app"
}

variable "db_password" {
  description = "Database user password"
  type        = string
  sensitive   = true
}

variable "db_tier" {
  description = "Cloud SQL tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_gb" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 20
}

variable "web_base_url" {
  description = "Base URL for the web app"
  type        = string
}

variable "api_base_url" {
  description = "Base URL for the API service"
  type        = string
}

variable "google_oauth_redirect_uri" {
  description = "OAuth redirect URI for Google"
  type        = string
}

variable "google_oauth_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "openai_model" {
  description = "Default OpenAI model"
  type        = string
  default     = "gpt-5.2"
}

variable "session_jwt_secret" {
  description = "Session JWT signing secret"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Fernet encryption key for tokens"
  type        = string
  sensitive   = true
}

variable "webhook_secret" {
  description = "Shared secret for local webhook validation"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pubsub_topic_name" {
  description = "Pub/Sub topic name for Gmail push"
  type        = string
  default     = "gmail-push-topic"
}

variable "queue_mode" {
  description = "Queue mode for incremental sync (local or cloud_tasks)"
  type        = string
  default     = "local"
}

variable "cloud_tasks_queue_name" {
  description = "Cloud Tasks queue name"
  type        = string
  default     = "gmail-sync-queue"
}

variable "cloud_tasks_location" {
  description = "Cloud Tasks location"
  type        = string
  default     = ""
}

variable "scheduler_timezone" {
  description = "Timezone for Cloud Scheduler jobs"
  type        = string
  default     = "UTC"
}

variable "renew_watches_cron" {
  description = "Cron schedule for Gmail watch renewal"
  type        = string
  default     = "0 2 * * *"
}

variable "digest_cron" {
  description = "Cron schedule for daily digest generation"
  type        = string
  default     = "0 8 * * *"
}

variable "snooze_sweep_cron" {
  description = "Cron schedule for snooze sweep"
  type        = string
  default     = "*/10 * * * *"
}

variable "api_cpu" {
  description = "CPU allocation for API service"
  type        = string
  default     = "1"
}

variable "api_memory" {
  description = "Memory allocation for API service"
  type        = string
  default     = "512Mi"
}

variable "worker_cpu" {
  description = "CPU allocation for worker service"
  type        = string
  default     = "1"
}

variable "worker_memory" {
  description = "Memory allocation for worker service"
  type        = string
  default     = "512Mi"
}

variable "kms_key_ring_name" {
  description = "KMS key ring name"
  type        = string
  default     = "clearview-keyring"
}

variable "kms_key_name" {
  description = "KMS crypto key name"
  type        = string
  default     = "clearview-token-key"
}

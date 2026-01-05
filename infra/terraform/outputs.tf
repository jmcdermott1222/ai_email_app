output "api_url" {
  description = "Cloud Run API URL"
  value       = google_cloud_run_service.api.status[0].url
}

output "worker_url" {
  description = "Cloud Run worker URL"
  value       = google_cloud_run_service.worker.status[0].url
}

output "cloudsql_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "pubsub_topic" {
  description = "Pub/Sub topic for Gmail push"
  value       = google_pubsub_topic.gmail_push.id
}

output "cloud_tasks_queue" {
  description = "Cloud Tasks queue name"
  value       = google_cloud_tasks_queue.incremental.name
}

output "scheduler_service_account" {
  description = "Cloud Scheduler invoker service account"
  value       = google_service_account.scheduler_invoker.email
}

output "pubsub_push_service_account" {
  description = "Pub/Sub push invoker service account"
  value       = google_service_account.pubsub_push.email
}

output "kms_key" {
  description = "KMS crypto key resource ID"
  value       = google_kms_crypto_key.token_key.id
}

resource "google_cloud_tasks_queue" "incremental" {
  name     = var.cloud_tasks_queue_name
  location = local.cloud_tasks_location

  rate_limits {
    max_dispatches_per_second = 5
    max_concurrent_dispatches = 5
  }

  retry_config {
    max_attempts = 5
    min_backoff  = "5s"
    max_backoff  = "300s"
  }

  depends_on = [google_project_service.services]
}

resource "google_cloud_scheduler_job" "renew_watches" {
  name      = "renew-watches"
  region    = var.region
  schedule  = var.renew_watches_cron
  time_zone = var.scheduler_timezone

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.worker.status[0].url}/internal/jobs/renew_watches"
    oidc_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_cloud_scheduler_job" "daily_digest" {
  name      = "daily-digest"
  region    = var.region
  schedule  = var.digest_cron
  time_zone = var.scheduler_timezone

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.worker.status[0].url}/internal/jobs/digest_run"
    oidc_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_cloud_scheduler_job" "snooze_sweep" {
  name      = "snooze-sweep"
  region    = var.region
  schedule  = var.snooze_sweep_cron
  time_zone = var.scheduler_timezone

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.worker.status[0].url}/internal/jobs/snooze_sweep"
    oidc_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.services]
}

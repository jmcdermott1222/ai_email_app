resource "google_pubsub_topic" "gmail_push" {
  name       = var.pubsub_topic_name
  depends_on = [google_project_service.services]
}

resource "google_pubsub_subscription" "gmail_push" {
  name  = "gmail-push-sub"
  topic = google_pubsub_topic.gmail_push.name

  push_config {
    push_endpoint = "${google_cloud_run_service.api.status[0].url}/webhooks/gmail/push"
    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
    }
  }

  ack_deadline_seconds = 30
}

resource "google_pubsub_topic_iam_member" "gmail_push_publisher" {
  topic  = google_pubsub_topic.gmail_push.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:gmail-api-push@system.gserviceaccount.com"
}

locals {
  cloud_tasks_location = var.cloud_tasks_location != "" ? var.cloud_tasks_location : var.region

  database_url = "postgresql+psycopg2://${var.db_user}:${var.db_password}@/${var.db_name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"

  api_env_vars = {
    API_BASE_URL              = var.api_base_url
    WEB_BASE_URL              = var.web_base_url
    GOOGLE_OAUTH_REDIRECT_URI = var.google_oauth_redirect_uri
    DATABASE_URL              = local.database_url
    OPENAI_MODEL              = var.openai_model
    SESSION_COOKIE_SECURE     = "true"
    PUBSUB_TOPIC              = google_pubsub_topic.gmail_push.id
    QUEUE_MODE                = var.queue_mode
    CLOUD_TASKS_PROJECT        = var.project_id
    CLOUD_TASKS_LOCATION       = local.cloud_tasks_location
    CLOUD_TASKS_QUEUE          = var.cloud_tasks_queue_name
    CLOUD_TASKS_SERVICE_ACCOUNT = google_service_account.tasks_invoker.email
    CLOUD_TASKS_TARGET_URL      = google_cloud_run_service.worker.status[0].url
  }

  api_secret_env = {
    GOOGLE_OAUTH_CLIENT_ID = google_secret_manager_secret.google_oauth_client_id.secret_id
    GOOGLE_OAUTH_CLIENT_SECRET = google_secret_manager_secret.google_oauth_client_secret.secret_id
    OPENAI_API_KEY         = google_secret_manager_secret.openai_api_key.secret_id
    SESSION_JWT_SECRET     = google_secret_manager_secret.session_jwt_secret.secret_id
    ENCRYPTION_KEY         = google_secret_manager_secret.encryption_key.secret_id
    WEBHOOK_SECRET         = google_secret_manager_secret.webhook_secret.secret_id
  }

  worker_env_vars = {
    API_BASE_URL              = var.api_base_url
    WEB_BASE_URL              = var.web_base_url
    GOOGLE_OAUTH_REDIRECT_URI = var.google_oauth_redirect_uri
    DATABASE_URL              = local.database_url
    OPENAI_MODEL              = var.openai_model
    SESSION_COOKIE_SECURE     = "true"
    PUBSUB_TOPIC              = google_pubsub_topic.gmail_push.id
  }

  worker_secret_env = {
    GOOGLE_OAUTH_CLIENT_ID = google_secret_manager_secret.google_oauth_client_id.secret_id
    GOOGLE_OAUTH_CLIENT_SECRET = google_secret_manager_secret.google_oauth_client_secret.secret_id
    OPENAI_API_KEY         = google_secret_manager_secret.openai_api_key.secret_id
    SESSION_JWT_SECRET     = google_secret_manager_secret.session_jwt_secret.secret_id
    ENCRYPTION_KEY         = google_secret_manager_secret.encryption_key.secret_id
  }
}

resource "google_sql_database_instance" "main" {
  name             = var.db_instance_name
  database_version = "POSTGRES_14"
  region           = var.region

  settings {
    tier      = var.db_tier
    disk_size = var.db_disk_gb
    ip_configuration {
      ipv4_enabled = true
    }
  }

  deletion_protection = false
  depends_on          = [google_project_service.services]
}

resource "google_sql_database" "app" {
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

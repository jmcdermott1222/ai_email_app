locals {
  required_services = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudkms.googleapis.com",
    "iamcredentials.googleapis.com",
    "gmail.googleapis.com",
  ])
}

resource "google_project_service" "services" {
  for_each           = local.required_services
  service            = each.value
  disable_on_destroy = false
}

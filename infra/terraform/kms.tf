resource "google_kms_key_ring" "token_ring" {
  name       = var.kms_key_ring_name
  location   = var.region
  depends_on = [google_project_service.services]
}

resource "google_kms_crypto_key" "token_key" {
  name            = var.kms_key_name
  key_ring        = google_kms_key_ring.token_ring.id
  rotation_period = "7776000s"
}

# bootstrap/gcp — GCS bucket for Terraform state
# Run once manually before the first OSD deployment.

resource "google_storage_bucket" "terraform_state" {
  name          = var.state_bucket_name
  location      = var.location
  force_destroy = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 10 # retain last 10 state versions
    }
  }

  uniform_bucket_level_access = true
}

output "state_bucket_name" {
  value = google_storage_bucket.terraform_state.name
}

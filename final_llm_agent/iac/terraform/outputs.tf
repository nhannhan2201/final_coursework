output "vm_public_ip" {
  description = "Public IP Address of Data Stack Compute Instance"
  value       = google_compute_instance.data_stack_vm.network_interface[0].access_config[0].nat_ip
}

output "gke_cluster_name" {
  description = "Google Kubernetes Engine Cluster Name"
  value       = google_container_cluster.gke_cluster.name
}

output "gke_cluster_endpoint" {
  description = "Endpoint IP for GKE Kubernetes Master API"
  value       = google_container_cluster.gke_cluster.endpoint
}

output "gcs_bucket_name" {
  description = "Google Cloud Storage Bucket Name"
  value       = google_storage_bucket.data_lake_bucket.name
}

output "gcloud_get_credentials_command" {
  description = "Command to configure kubectl credentials for the GKE cluster"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.gke_cluster.name} --zone ${var.gcp_zone} --project ${var.gcp_project_id}"
}

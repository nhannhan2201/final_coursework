variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "your-gcp-project-id"
}

variable "gcp_region" {
  description = "GCP Region for infrastructure deployment"
  type        = string
  default     = "asia-southeast1"
}

variable "gcp_zone" {
  description = "GCP Zone for Compute VM & GKE cluster"
  type        = string
  default     = "asia-southeast1-a"
}

variable "vm_machine_type" {
  description = "Machine type for Data Lakehouse Stack VM"
  type        = string
  default     = "e2-standard-4"
}

variable "gke_node_machine_type" {
  description = "Machine type for GKE Worker Nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "gke_initial_node_count" {
  description = "Initial number of nodes in GKE Node Pool"
  type        = number
  default     = 2
}

variable "storage_bucket_name" {
  description = "Unique Google Cloud Storage bucket name"
  type        = string
  default     = "ecom-mlops-datalake-bucket"
}

variable "enable_gpu_node_pool" {
  description = "Flag to enable GPU Node Pool for LLM Inference"
  type        = bool
  default     = false
}

variable "gpu_type" {
  description = "NVIDIA GPU Accelerator type for GKE"
  type        = string
  default     = "nvidia-tesla-t4"
}


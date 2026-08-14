terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# ==============================================================================
# 1. VPC NETWORK & FIREWALL RULES
# ==============================================================================
resource "google_compute_network" "vpc_network" {
  name                    = "ecom-mlops-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "allow_data_stack_ports" {
  name    = "allow-data-stack-ports"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443", "8000", "8080", "8081", "9000", "9001", "9002", "6379", "9092"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["data-stack-vm"]
}

# ==============================================================================
# 2. GOOGLE CLOUD STORAGE BUCKET (OBJECT STORAGE FOR DATA LAKE)
# ==============================================================================
resource "google_storage_bucket" "data_lake_bucket" {
  name                        = "${var.gcp_project_id}-${var.storage_bucket_name}"
  location                    = var.gcp_region
  force_destroy               = true
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# ==============================================================================
# 3. COMPUTE ENGINE VM (FOR DATA LAKEHOUSE STACK: TRINO, MINIO, SPARK, AIRFLOW)
# ==============================================================================
resource "google_compute_instance" "data_stack_vm" {
  name         = "ecom-data-stack-vm"
  machine_type = var.vm_machine_type
  zone         = var.gcp_zone

  tags = ["data-stack-vm"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 80 # 80 GB SSD disk for Data Lakehouse & Containers
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.name
    access_config {
      // Ephemeral public IP address
    }
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

# ==============================================================================
# 4. GKE CLUSTER (FOR K8S NATIVE AI AGENT & MICROSERVICES SYSTEM)
# ==============================================================================
resource "google_container_cluster" "gke_cluster" {
  name     = "ecom-kagent-gke-cluster"
  location = var.gcp_zone

  network    = google_compute_network.vpc_network.name
  subnetwork = google_compute_network.vpc_network.name

  remove_default_node_pool = true
  initial_node_count       = 1

  deletion_protection = false
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "ecom-kagent-node-pool"
  location   = var.gcp_zone
  cluster    = google_container_cluster.gke_cluster.name
  node_count = var.gke_initial_node_count

  node_config {
    preemptible  = false
    machine_type = var.gke_node_machine_type

    # OAuth scopes required for GKE nodes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      environment = "production"
      role        = "ai-agent-microservices"
    }

    tags = ["gke-node", "ecom-agent-cluster"]
  }
}

# ==============================================================================
# 5. OPTIONAL GPU NODE POOL (FOR HIGH-PERFORMANCE LLM INFERENCE - VLLM / QWEN)
# ==============================================================================
resource "google_container_node_pool" "gpu_nodes" {
  count      = var.enable_gpu_node_pool ? 1 : 0
  name       = "ecom-gpu-llm-node-pool"
  location   = var.gcp_zone
  cluster    = google_container_cluster.gke_cluster.name
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "g2-standard-4" # GPU-optimized instance

    guest_accelerator {
      type  = var.gpu_type
      count = 1
      gpu_sharing_config {
        gpu_sharing_strategy = "TIME_SHARING"
        max_shared_clients_per_gpu = 2
      }
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      environment = "production"
      role        = "llm-gpu-inference"
    }

    tags = ["gke-gpu-node", "llm-inference"]
  }
}


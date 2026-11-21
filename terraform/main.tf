# Provider dikonfigurasi supaya `terraform plan` bisa dijalankan TANPA akun AWS sungguhan.
# Tidak ada access key di kode. Pada penggunaan nyata, hapus opsi skip_* dan pakai
# kredensial dari environment (AWS_PROFILE / OIDC role), bukan dari file.
provider "aws" {
  region = var.region

  skip_credentials_validation = var.offline_plan
  skip_requesting_account_id  = var.offline_plan
  skip_metadata_api_check     = var.offline_plan
  skip_region_validation      = var.offline_plan
  access_key                  = var.offline_plan ? "dummy" : null
  secret_key                  = var.offline_plan ? "dummy" : null
}

locals {
  name = "${var.project}-${var.environment}"
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

module "network" {
  source = "./modules/network"

  name     = local.name
  vpc_cidr = var.vpc_cidr
  azs      = var.azs
  tags     = local.tags
}

module "kubernetes" {
  source = "./modules/kubernetes"

  name               = local.name
  private_subnet_ids = module.network.private_subnet_ids
  node_instance_type = var.node_instance_type
  node_desired_size  = var.node_desired_size
  node_min_size      = var.node_min_size
  node_max_size      = var.node_max_size
  tags               = local.tags
}

module "database" {
  source = "./modules/database"

  name                = local.name
  vpc_id              = module.network.vpc_id
  private_subnet_ids  = module.network.private_subnet_ids
  allowed_sg_id       = module.kubernetes.cluster_security_group_id
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  multi_az            = var.db_multi_az
  deletion_protection = var.db_deletion_protection
  skip_final_snapshot = var.db_skip_final_snapshot
  tags                = local.tags
}

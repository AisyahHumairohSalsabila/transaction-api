resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

# Isolasi jaringan: port 5432 hanya terbuka untuk security group node Kubernetes.
resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "PostgreSQL access from Kubernetes nodes only"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_vpc_security_group_ingress_rule" "from_nodes" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = var.allowed_sg_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_db_instance" "this" {
  identifier     = "${var.name}-pg"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_encrypted = true

  db_name  = "transactions"
  username = "trx_admin"

  # Password dibuat dan disimpan otomatis di AWS Secrets Manager.
  # Tidak ada password di kode maupun di state yang bisa dibaca sembarang orang.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  multi_az                = var.multi_az
  backup_retention_period = 7
  deletion_protection     = var.deletion_protection
  skip_final_snapshot     = var.skip_final_snapshot

  tags = var.tags
}

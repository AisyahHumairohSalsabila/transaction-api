variable "name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "allowed_sg_id" {
  description = "Hanya security group ini (node Kubernetes) yang boleh mengakses database."
  type        = string
}
variable "instance_class" { type = string }
variable "allocated_storage" { type = number }
variable "multi_az" { type = bool }
variable "deletion_protection" { type = bool }
variable "skip_final_snapshot" { type = bool }
variable "tags" {
  type    = map(string)
  default = {}
}

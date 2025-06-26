variable "aws_region" { default = "us-east-1" }
variable "aws_profile" { default = "default" }
variable "aws_credentials_files" {
  type    = list(string)
  default = ["../_credentials/aws_learner_lab_credentials"]
}
variable "ami_id" { default = "ami-053b0d53c279acc90" }
variable "instance_type" { default = "t3.xlarge" }
variable "key_name" { default = "labsuser" }
variable "ssh_ingress_cidr" { default = "0.0.0.0/0" }
variable "service_names" {
  description = "Liste des services à déployer"
  type        = list(string)
  default     = [
    "api",
    "sources_api",
    "lakehouse",
    "postgres",
    "elasticsearch",
    "prometheus",
    "grafana",
    "api_ml",
    "ui_api_ml",
  ]
}

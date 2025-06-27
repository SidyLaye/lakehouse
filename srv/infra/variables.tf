variable "aws_region" { default = "us-east-1" }           # Région AWS par défaut
variable "aws_profile" { default = "default" }              # Profil AWS par défaut
variable "aws_credentials_files" {
  type    = list(string)
  default = ["../_credentials/aws_learner_lab_credentials"]  # Chemin du fichier d'identifiants AWS
}
<<<<<<< HEAD
variable "ami_id" { default = "ami-053b0d53c279acc90" }     # ID AMI Ubuntu par défaut
variable "instance_type" { default = "t3.small" }           # Type d'instance EC2 par défaut
variable "key_name" { default = "labsuser" }                # Nom de la clé SSH
variable "ssh_ingress_cidr" { default = "0.0.0.0/0" }       # CIDR autorisé pour SSH
=======
variable "ami_id" { default = "ami-053b0d53c279acc90" }
variable "instance_type" { default = "t3.xlarge" }
variable "key_name" { default = "labsuser" }
variable "ssh_ingress_cidr" { default = "0.0.0.0/0" }
>>>>>>> cb5b0ec07bd2b86755c768f132cd95d74bc651aa
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

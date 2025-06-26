provider "aws" {
  region                   = var.aws_region
  profile                  = var.aws_profile
  shared_credentials_files = var.aws_credentials_files
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["*ubuntu-*24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# --- Réseau et Internet ---
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "public-route-table"
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "internal" {
  name        = "internal"
  description = "Allow all internal communication"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "ssh_ingress" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = [var.ssh_ingress_cidr]
  security_group_id = aws_security_group.internal.id
}

resource "aws_security_group" "public" {
  name        = "public"
  description = "Allow public access only for specific services"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 9200
    to_port     = 9200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- Instances EC2 ---
locals {
  services        = var.service_names
  public_services = var.service_names
}

resource "aws_instance" "services" {
  count                       = length(local.services)
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.main.id
  key_name                    = var.key_name
  vpc_security_group_ids      = compact([
    aws_security_group.internal.id,
    contains(local.public_services, local.services[count.index]) ? aws_security_group.public.id : null
  ])
  associate_public_ip_address = contains(local.public_services, local.services[count.index])

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name = local.services[count.index]
  }

  user_data = <<EOF
#!/bin/bash
hostnamectl set-hostname ${local.services[count.index]}
echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/99-ubuntu-nopasswd
chmod 440 /etc/sudoers.d/99-ubuntu-nopasswd
EOF
}

output "services_private_ips" {
  value = { for idx, name in local.services : name => aws_instance.services[idx].private_ip }
}

output "services_public_ips" {
  value = { for idx, name in local.services : name => aws_instance.services[idx].public_ip }
}

# --- DNS privé interne (Route 53) ---
resource "aws_route53_zone" "private" {
  name = "internal."
  vpc {
    vpc_id = aws_vpc.main.id
  }
}

resource "aws_route53_record" "services" {
  for_each = {
    for idx, name in local.services :
    name => aws_instance.services[idx].private_ip
  }

  zone_id = aws_route53_zone.private.zone_id
  name    = "${each.key}.internal"
  type    = "A"
  ttl     = 60
  records = [each.value]
}

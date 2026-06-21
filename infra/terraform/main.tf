terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }

  backend "local" {}
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

variable "ssh_public_key" {
  type    = string
  default = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPPc4bcYmZcZJ49BQZ0M4J1ciMz/qPFMNBM2sAU99wF+ dishify-deploy"
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "deploy" {
  name       = "dishify-deploy"
  public_key = var.ssh_public_key
}

resource "hcloud_firewall" "dishify" {
  name = "dishify-fw"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server" "dishify" {
  name        = "dishify"
  image       = "ubuntu-24.04"
  server_type = "cx23"
  location    = "nbg1"

  ssh_keys = [hcloud_ssh_key.deploy.id]

  firewall_ids = [hcloud_firewall.dishify.id]

  labels = {
    project = "dishify"
  }
}

output "server_ip" {
  value = hcloud_server.dishify.ipv4_address
}

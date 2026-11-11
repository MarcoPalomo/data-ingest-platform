variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "workspace_name" {
  type = string
}

variable "sku" {
  type    = string
  default = "standard"
}

variable "create_user_assigned_identity" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}

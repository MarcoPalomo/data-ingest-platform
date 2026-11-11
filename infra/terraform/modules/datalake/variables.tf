variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "storage_account_name" {
  type = string
}

variable "containers" {
  type    = list(string)
  default = ["raw", "processed", "serving"]
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "network_rules" {
  type    = object({
    default_action = string
    bypass         = optional(list(string))
    ip_rules       = optional(list(string))
  })
  default = {
    default_action = "Allow"
    bypass         = ["AzureServices"]
    ip_rules       = []
  }
}

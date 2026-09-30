terraform {
  backend "http" {
    address        = "https://tf-rest.uktme.cisco.com/state/tn-isovalent"
    lock_address   = "https://tf-rest.uktme.cisco.com/state/tn-isovalent"
    unlock_address = "https://tf-rest.uktme.cisco.com/state/tn-isovalent"
  }
}

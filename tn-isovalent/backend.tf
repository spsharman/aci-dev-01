terraform {
  backend "s3" {
    bucket         = "isovalent.tf-state-bucket"
    key            = "aci-dev-01/tn-isovalent.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "terraform-locks"
    profile        = "isovalent-demo"
  }
}

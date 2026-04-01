variable "REGISTRY" { default = "ghcr.io" }
variable "OWNER"    { default = "" }
variable "TAG"      { default = "latest" }

function "img" {
  params = [name]
  result = "${REGISTRY}/${OWNER}/wallet-${name}"
}

group "default" {
  targets = ["backend", "frontend", "backup", "report-service"]
}

target "backend" {
  context    = "."
  dockerfile = "docker/prod/backend.Dockerfile"
  tags       = ["${img("backend")}:latest", "${img("backend")}:${TAG}"]
  cache-from = ["type=gha,scope=backend"]
  cache-to   = ["type=gha,scope=backend,mode=max"]
}

target "frontend" {
  context    = "."
  dockerfile = "docker/prod/frontend.Dockerfile"
  tags       = ["${img("frontend")}:latest", "${img("frontend")}:${TAG}"]
  cache-from = ["type=gha,scope=frontend"]
  cache-to   = ["type=gha,scope=frontend,mode=max"]
}

target "backup" {
  context    = "."
  dockerfile = "docker/backup/Dockerfile"
  tags       = ["${img("backup")}:latest", "${img("backup")}:${TAG}"]
  cache-from = ["type=gha,scope=backup"]
  cache-to   = ["type=gha,scope=backup,mode=max"]
}

target "report-service" {
  context    = "."
  dockerfile = "docker/prod/report-service.Dockerfile"
  tags       = ["${img("report-service")}:latest", "${img("report-service")}:${TAG}"]
  cache-from = ["type=gha,scope=report-service"]
  cache-to   = ["type=gha,scope=report-service,mode=max"]
}
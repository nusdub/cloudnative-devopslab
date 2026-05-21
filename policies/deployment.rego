package cloudnative.devopslab.guardrails

import rego.v1

default allow := false

allow if {
	count(deny) == 0
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	not container.resources.requests.cpu
	msg := sprintf("container %s must define cpu request", [container.name])
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	not container.resources.requests.memory
	msg := sprintf("container %s must define memory request", [container.name])
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	not container.resources.limits.cpu
	msg := sprintf("container %s must define cpu limit", [container.name])
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	not container.resources.limits.memory
	msg := sprintf("container %s must define memory limit", [container.name])
}

deny contains msg if {
	input.kind == "Deployment"
	input.spec.strategy.rollingUpdate.maxUnavailable != 0
	msg := "production rollout must keep maxUnavailable at 0 for this small-replica service"
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	not container.readinessProbe
	msg := sprintf("container %s must define readinessProbe", [container.name])
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	not container.livenessProbe
	msg := sprintf("container %s must define livenessProbe", [container.name])
}

deny contains msg if {
	input.kind == "Deployment"
	container := input.spec.template.spec.containers[_]
	endswith(container.image, ":latest")
	msg := sprintf("container %s uses mutable latest tag", [container.name])
}

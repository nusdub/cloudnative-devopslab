{{- define "cloudnative-devopslab.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "cloudnative-devopslab.fullname" -}}
{{- default (include "cloudnative-devopslab.name" .) .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "cloudnative-devopslab.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "cloudnative-devopslab.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "cloudnative-devopslab.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cloudnative-devopslab.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

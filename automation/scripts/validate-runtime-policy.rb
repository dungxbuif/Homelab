#!/usr/bin/env ruby
# frozen_string_literal: true

require "optparse"
require "psych"
require "yaml"

options = { active: nil, retired: nil }
OptionParser.new do |parser|
  parser.on("--active PATH") { |path| options[:active] = path }
  parser.on("--retired PATH") { |path| options[:retired] = path }
end.parse!

abort("--active and --retired are required") unless options[:active] && options[:retired]

def duplicate_mapping_keys(node, path = "$", errors = [])
  case node
  when Psych::Nodes::Mapping
    seen = {}
    node.children.each_slice(2) do |key, value|
      key_name = key.respond_to?(:value) ? key.value : key.to_s
      errors << "duplicate mapping key #{path}.#{key_name}" if seen[key_name]
      seen[key_name] = true
      duplicate_mapping_keys(value, "#{path}.#{key_name}", errors)
    end
  when Psych::Nodes::Sequence
    node.children.each_with_index do |child, index|
      duplicate_mapping_keys(child, "#{path}[#{index}]", errors)
    end
  end
  errors
end

def load_yaml(path)
  text = File.read(path)
  ast_errors = duplicate_mapping_keys(Psych.parse_stream(text))
  abort(ast_errors.join("\n")) unless ast_errors.empty?
  YAML.safe_load(text, aliases: false) || {}
rescue Psych::Exception, Errno::ENOENT => error
  abort("cannot load #{path}: #{error.message}")
end

def rows(document, key)
  value = document.fetch(key, [])
  abort("#{key} must be an array") unless value.is_a?(Array)
  value
end

def validate_unique_ids(items, label, errors)
  ids = items.map { |item| item["id"] }
  errors << "#{label} entries require id" if ids.any?(&:nil?)
  ids.compact.group_by(&:itself).each do |id, matches|
    errors << "duplicate #{label} id: #{id}" if matches.length > 1
  end
end

active = load_yaml(options[:active])
retired = load_yaml(options[:retired])
errors = []

errors << "active policy schema_version must be 1" unless active["schema_version"] == 1
errors << "retired policy schema_version must be 1" unless retired["schema_version"] == 1
errors << "retired policy lifecycle must be historical" unless retired["lifecycle"] == "historical"

hosts = rows(active, "hosts")
services = rows(active, "services")
routes = rows(active, "routes")
backup_classes = rows(active, "backup_classes")
validate_unique_ids(hosts, "host", errors)
validate_unique_ids(services, "service", errors)
validate_unique_ids(routes, "route", errors)
validate_unique_ids(backup_classes, "backup class", errors)

host_ids = hosts.map { |host| host["id"] }.compact
service_by_id = services.to_h { |service| [service["id"], service] }

hosts.each do |host|
  errors << "historical host #{host["id"]} cannot be active" unless host["lifecycle"] == "active"
  if host["id"].to_s.match?(/k8s|kube|kubernetes/i)
    errors << "Kubernetes host target is forbidden: #{host["id"]}"
  end
end

services.each do |service|
  errors << "service #{service["id"]} references unknown host #{service["host"]}" unless host_ids.include?(service["host"])
  errors << "service #{service["id"]} must be active" unless service["lifecycle"] == "active"
  ports = Array(service["public_ports"])
  errors << "service #{service["id"]} has forbidden public database/cache port" if ports.any? { |port| [5432, 6379, 16379, 8787].include?(port.to_i) }
end

kubernetes_targets = 0
services.each do |service|
  kubernetes_targets += 1 if service["class"].to_s.match?(/kubernetes|kube-vip/i)
end
routes.each do |route|
  service = service_by_id[route["service"]]
  errors << "route #{route["id"]} references unknown service #{route["service"]}" unless service
  next unless service

  errors << "route #{route["id"]} has unsupported exposure" unless %w[public lan netbird internal].include?(route["exposure"])
  if route["exposure"] == "public" && %w[database cache backup control_plane].include?(service["class"])
    errors << "public route #{route["id"]} targets protected service class #{service["class"]}"
  end
  if service["class"].to_s.match?(/kubernetes|kube-vip/i)
    kubernetes_targets += 1
  end
end

retired_ids = []
%w[hosts services routes].each do |key|
  retired_ids.concat(rows(retired, key).map { |item| item["id"] }.compact)
end
active_ids = (host_ids + services.map { |item| item["id"] }.compact + routes.map { |item| item["id"] }.compact)
errors << "historical target is active: #{(active_ids & retired_ids).join(", ")}" unless (active_ids & retired_ids).empty?

report = {
  "status" => errors.empty? ? "ok" : "error",
  "errors" => errors,
  "hosts" => hosts.length,
  "services" => services.length,
  "routes" => routes.length,
  "backup_classes" => backup_classes.length,
  "kubernetes_targets" => kubernetes_targets
}

puts report.to_yaml
exit(errors.empty? ? 0 : 1)

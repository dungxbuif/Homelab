#!/usr/bin/env ruby
# frozen_string_literal: true

require "minitest/autorun"
require "open3"
require "tmpdir"
require "yaml"

ROOT = File.expand_path("../..", __dir__)
VALIDATOR = File.join(ROOT, "automation", "scripts", "validate-runtime-policy.rb")
ACTIVE = File.join(ROOT, "automation", "policies", "active-runtime.yaml")
RETIRED = File.join(ROOT, "automation", "policies", "retired-runtime.yaml")

class RuntimePolicyTest < Minitest::Test
  def run_validator(active: ACTIVE, retired: RETIRED)
    Open3.capture3("ruby", VALIDATOR, "--active", active, "--retired", retired)
  end

  def test_current_policy_is_valid_and_has_no_kubernetes_target
    stdout, stderr, status = run_validator

    assert status.success?, "validator failed: #{stdout}\n#{stderr}"
    report = YAML.safe_load(stdout)
    assert_equal "ok", report.fetch("status")
    assert_equal 0, report.fetch("errors").length
    assert_equal 0, report.fetch("kubernetes_targets")
  end

  def test_duplicate_ids_are_rejected
    Dir.mktmpdir do |dir|
      active = File.join(dir, "active.yml")
      File.write(active, <<~YAML)
        schema_version: 1
        hosts:
          - id: pi5
            lifecycle: active
          - id: pi5
            lifecycle: active
        services: []
        routes: []
        backup_classes: []
      YAML

      stdout, stderr, status = run_validator(active: active)

      refute status.success?
      assert_includes "#{stdout}\n#{stderr}", "duplicate"
    end
  end

  def test_historical_host_cannot_be_active
    Dir.mktmpdir do |dir|
      active = File.join(dir, "active.yml")
      retired = File.join(dir, "retired.yml")
      File.write(active, <<~YAML)
        schema_version: 1
        hosts:
          - id: old-node
            lifecycle: historical
        services: []
        routes: []
        backup_classes: []
      YAML
      File.write(retired, "schema_version: 1\nlifecycle: historical\nhosts: []\nservices: []\nroutes: []\n")

      stdout, stderr, status = run_validator(active: active, retired: retired)

      refute status.success?
      assert_includes "#{stdout}\n#{stderr}", "historical"
    end
  end

  def test_forbidden_public_data_route_is_rejected
    Dir.mktmpdir do |dir|
      active = File.join(dir, "active.yml")
      File.write(active, <<~YAML)
        schema_version: 1
        hosts:
          - id: pi5
            lifecycle: active
        services:
          - id: postgres
            host: pi5
            class: database
            lifecycle: active
        routes:
          - id: raw-postgres
            service: postgres
            exposure: public
        backup_classes: []
      YAML

      stdout, stderr, status = run_validator(active: active)

      refute status.success?
      assert_includes "#{stdout}\n#{stderr}", "public"
    end
  end
end

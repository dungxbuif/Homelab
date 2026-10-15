#!/usr/bin/env ruby
# frozen_string_literal: true

require 'minitest/autorun'
require 'yaml'

class SemaphoreTemplateContractTest < Minitest::Test
  ROOT = File.expand_path('..', __dir__)
  TEMPLATE_DIR = File.join(ROOT, 'templates')
  TEMPLATE_NAMES = %w[
    host-audit
    ansible-check
    ansible-apply
    tofu-plan
    tofu-apply-approved
    route-publish
    backup-client-release
    app-deploy
    rollback
  ].freeze
  REQUIRED_KEYS = %w[
    name
    description
    repository
    revision
    execution_image
    inventory
    workspace
    variables
    approval
    post_check
  ].freeze

  def test_every_operator_template_has_the_shared_contract
    TEMPLATE_NAMES.each do |name|
      path = File.join(TEMPLATE_DIR, "#{name}.yaml")
      assert File.file?(path), "missing template #{name}"
      data = YAML.load_file(path)
      REQUIRED_KEYS.each { |key| assert data.key?(key), "#{name} missing #{key}" }
      assert_equal 'AUTOMATION_EE_IMAGE_DIGEST', data.fetch('execution_image').fetch('digest_variable')
      assert_equal true, data.fetch('execution_image').fetch('immutable')
      assert data.fetch('variables').is_a?(Array)
      assert data.fetch('post_check').fetch('command').to_s.length.positive?
    end
  end

  def test_mutation_and_approval_boundaries_are_explicit
    assert_equal false, YAML.load_file(File.join(TEMPLATE_DIR, 'host-audit.yaml')).fetch('approval').fetch('required')
    assert_equal false, YAML.load_file(File.join(TEMPLATE_DIR, 'ansible-check.yaml')).fetch('approval').fetch('required')
    assert_equal false, YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-plan.yaml')).fetch('approval').fetch('required')

    %w[ansible-apply tofu-apply-approved route-publish backup-client-release app-deploy rollback].each do |name|
      data = YAML.load_file(File.join(TEMPLATE_DIR, "#{name}.yaml"))
      assert_equal true, data.fetch('approval').fetch('required'), "#{name} must require approval"
      assert_includes data.fetch('approval').fetch('roles'), 'Manager'
    end
  end

  def test_backup_client_release_is_fixed_scope
    data = YAML.load_file(File.join(TEMPLATE_DIR, 'backup-client-release.yaml'))
    refute data.key?('availability')
    assert_equal 'Semaphore inventory 6 (Pi5 backup client release)', data.fetch('inventory')
    assert_equal ['Manager'], data.fetch('approval').fetch('roles')
    names = data.fetch('variables').map { |variable| variable.fetch('name') }
    assert_equal %w[backup_client_release_approved change_message], names
    refute_match(/service_id|image_digest|route_set|target_environment/, data.to_yaml)
    assert_match(/--limit pi5/, data.fetch('command'))
  end

  def test_backup_client_release_is_manager_only
    resources = YAML.load_file(File.join(ROOT, 'project-resources.yaml'))
    viewer = resources.fetch('roles').find { |role| role.fetch('name') == 'Viewer' }
    runner = resources.fetch('roles').find { |role| role.fetch('name') == 'Task Runner' }
    manager = resources.fetch('roles').find { |role| role.fetch('name') == 'Manager' }
    refute_includes viewer.fetch('allowed_templates'), 'backup-client-release'
    refute_includes runner.fetch('allowed_templates'), 'backup-client-release'
    assert_includes manager.fetch('allowed_templates'), 'backup-client-release'
  end

  def test_project_roles_and_execution_image_are_pinned
    data = YAML.load_file(File.join(ROOT, 'project-resources.yaml'))
    assert_equal ['Manager', 'Task Runner', 'Viewer'], data.fetch('roles').map { |role| role.fetch('name') }.sort
    assert_equal 'AUTOMATION_EE_IMAGE_DIGEST', data.fetch('execution_image').fetch('digest_variable')
    assert_equal true, data.fetch('execution_image').fetch('immutable')
    refute_match(/latest/, data.to_yaml)
  end

  def test_design_only_templates_are_not_exposed_to_operator_roles
    resources = YAML.load_file(File.join(ROOT, 'project-resources.yaml'))
    design_only = TEMPLATE_NAMES.select do |name|
      YAML.load_file(File.join(TEMPLATE_DIR, "#{name}.yaml"))['availability'] == 'design_only'
    end
    refute_empty design_only
    resources.fetch('roles').each do |role|
      design_only.each do |name|
        refute_includes role.fetch('allowed_templates'), name,
                        "#{name} is design-only and cannot be exposed to #{role.fetch('name')}"
      end
    end
  end

  def test_generic_host_audit_is_design_only_until_dynamic_inventory_is_reconciled
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'host-audit.yaml'))
    assert_equal 'design_only', template.fetch('availability')
    resources = YAML.load_file(File.join(ROOT, 'project-resources.yaml'))
    resources.fetch('roles').each do |role|
      refute_includes role.fetch('allowed_templates'), 'host-audit'
    end
  end

  def test_provisioning_change_summary_matches_http_creation
    play = YAML.load_file(File.join(ROOT, 'playbooks/db-provision.yml')).first
    task = play.fetch('tasks').find { |entry| entry['register'] == 'provision_response' }
    assert_equal 'provision_response.status == 201', task['changed_when']
    assert_equal true, task['no_log']
    assert_equal [200, 201], task.fetch('ansible.builtin.uri').fetch('status_code')
  end
end

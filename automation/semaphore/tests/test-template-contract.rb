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

    %w[ansible-apply tofu-apply-approved route-publish app-deploy rollback].each do |name|
      data = YAML.load_file(File.join(TEMPLATE_DIR, "#{name}.yaml"))
      assert_equal true, data.fetch('approval').fetch('required'), "#{name} must require approval"
      assert_includes data.fetch('approval').fetch('roles'), 'Manager'
    end
  end

  def test_project_roles_and_execution_image_are_pinned
    data = YAML.load_file(File.join(ROOT, 'project-resources.yaml'))
    assert_equal ['Manager', 'Task Runner', 'Viewer'], data.fetch('roles').map { |role| role.fetch('name') }.sort
    assert_equal 'AUTOMATION_EE_IMAGE_DIGEST', data.fetch('execution_image').fetch('digest_variable')
    assert_equal true, data.fetch('execution_image').fetch('immutable')
    refute_match(/latest/, data.to_yaml)
  end
end

#!/usr/bin/env ruby
# frozen_string_literal: true

require 'minitest/autorun'
require 'digest'
require 'json'
require 'fileutils'
require 'open3'
require 'tmpdir'
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

  def test_route_publish_stages_selected_route_set_and_fails_closed
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'route-publish.yaml'))
    names = template.fetch('variables').map { |variable| variable.fetch('name') }
    assert_equal %w[route_set change_message], names
    route_set = template.fetch('variables').find { |variable| variable.fetch('name') == 'route_set' }
    assert_equal %w[public lan netbird], route_set.fetch('values')
    refute_match(/\b(ssh|scp|curl|docker|kubectl|tofu)\b/, template.fetch('command'))

    post_check = template.fetch('post_check')
    assert_equal 'artifacts/routes-post-check.json', post_check.fetch('artifact')
    assert_match(/routes-post-check\.json/, post_check.fetch('command'))
    assert_match(/rendered_artifact/, post_check.fetch('command'))

    Dir.mktmpdir('route-publish-contract') do |dir|
      install_route_publish_fixture(dir)
      stdout, stderr, status = run_command(template.fetch('command'), dir,
                                            'route_set' => 'public')
      assert status.success?, "route staging failed: #{stdout}\n#{stderr}"

      rendered_path = File.join(dir, 'artifacts/routes-public.yml')
      receipt_path = File.join(dir, 'artifacts/routes-post-check.json')
      assert_path_with_content(dir, 'artifacts/routes-public.yml')
      assert_path_with_content(dir, 'artifacts/routes-post-check.json')

      catalog = YAML.load_file(File.join(dir, 'automation/routes/catalog.yml'))
      expected_ids = catalog.fetch('routes').select { |route| route.fetch('exposure') == 'public' }
        .map { |route| route.fetch('id') }.sort
      rendered = YAML.safe_load(File.read(rendered_path), aliases: true)
      assert_equal expected_ids, rendered.fetch('http').fetch('routers').keys.sort

      receipt = JSON.parse(File.read(receipt_path))
      assert_equal 'staged', receipt.fetch('status')
      assert_equal 'public', receipt.fetch('route_set')
      assert_equal 'validated', receipt.fetch('runtime_policy')
      assert_equal false, receipt.fetch('published')
      assert_equal false, receipt.fetch('production_contacted')
      assert_equal 'artifacts/routes-public.yml', receipt.fetch('rendered_artifact')
      assert_equal expected_ids.length, receipt.fetch('route_count')

      stdout, stderr, status = run_command(post_check.fetch('command'), dir)
      assert status.success?, "route post-check failed: #{stdout}\n#{stderr}"

      FileUtils.rm(rendered_path)
      _, stderr, status = run_command(post_check.fetch('command'), dir)
      refute status.success?, "post-check passed without rendered artifact: #{stderr}"

      FileUtils.rm(receipt_path)
      _, stderr, status = run_command(post_check.fetch('command'), dir)
      refute status.success?, "post-check passed without receipt: #{stderr}"
    end
  end

  def test_route_publish_rejects_an_unsupported_route_set_before_writing_artifacts
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'route-publish.yaml'))

    Dir.mktmpdir('route-publish-invalid-set') do |dir|
      install_route_publish_fixture(dir)
      _, stderr, status = run_command(template.fetch('command'), dir,
                                       'route_set' => 'production')
      refute status.success?, 'unsupported route_set unexpectedly succeeded'
      assert_match(/route_set/, stderr)
      refute File.exist?(File.join(dir, 'artifacts/routes-post-check.json'))
    end
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

  def test_tofu_plan_writes_the_binary_and_review_artifacts_used_by_post_check
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-plan.yaml'))
    names = template.fetch('variables').map { |variable| variable.fetch('name') }
    assert_equal %w[target plan_artifact_id change_message], names

    artifacts = template.fetch('post_check').fetch('artifacts', [])
    assert_equal %w[
      artifacts/vm100.tfplan
      artifacts/vm100.plan.txt
      artifacts/vm100.plan.json
      artifacts/vm100.plan.sha256
      artifacts/vm100.plan.manifest.json
    ], artifacts

    Dir.mktmpdir('tofu-plan-contract') do |dir|
      install_fake_tofu(dir)
      stdout, stderr, status = run_command(template.fetch('command'), dir,
                                            'plan_artifact_id' => 'plan-42')

      assert status.success?, "plan command failed: #{stdout}\n#{stderr}"
      artifacts.each { |path| assert_path_with_content(dir, path) }
      manifest = JSON.parse(File.read(File.join(dir, 'artifacts/vm100.plan.manifest.json')))
      assert_equal 'plan-42', manifest.fetch('plan_id')
      assert_equal File.read(File.join(dir, 'artifacts/vm100.plan.sha256')).strip,
                   manifest.fetch('plan_sha256')
    end
  end

  def test_tofu_plan_post_check_validates_the_json_plan_gate
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-plan.yaml'))

    Dir.mktmpdir('tofu-plan-post-check') do |dir|
      install_fake_tofu(dir)
      install_plan_guard(dir)
      _, stderr, status = run_command(template.fetch('command'), dir,
                                       'plan_artifact_id' => 'plan-42')
      assert status.success?, stderr

      stdout, stderr, status = run_command(template.fetch('post_check').fetch('command'), dir)
      assert status.success?, "post-check failed: #{stdout}\n#{stderr}"

      json_path = File.join(dir, 'artifacts/vm100.plan.json')
      assert File.file?(json_path), 'plan command missing JSON artifact'
      if File.file?(json_path)
        FileUtils.rm(json_path)
        _, stderr, status = run_command(template.fetch('post_check').fetch('command'), dir)
        refute status.success?, "post-check unexpectedly passed: #{stderr}"
      end
    end
  end

  def test_tofu_apply_requires_the_approved_plan_hash_and_binding_artifacts
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-apply-approved.yaml'))
    names = template.fetch('variables').map { |variable| variable.fetch('name') }

    assert_equal %w[target approved_plan_id approved_plan_hash change_message], names
    assert_equal %w[
      artifacts/vm100-approved-plan.json
      artifacts/vm100-post-apply.txt
    ], template.fetch('post_check').fetch('artifacts')
  end

  def test_tofu_apply_rejects_a_mismatched_approved_plan_id_before_apply
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-apply-approved.yaml'))

    Dir.mktmpdir('tofu-apply-id-mismatch') do |dir|
      install_fake_tofu(dir)
      install_plan_guard(dir)
      write_plan_bundle(dir, plan_id: 'plan-42')
      _, stderr, status = run_command(template.fetch('command'), dir,
                                       'approved_plan_id' => 'plan-99',
                                       'approved_plan_hash' => plan_hash(dir))

      refute status.success?
      assert_match(/approved plan/i, stderr)
      refute File.exist?(File.join(dir, 'apply.called'))
    end
  end

  def test_tofu_apply_rejects_a_mismatched_approved_plan_hash_before_apply
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-apply-approved.yaml'))

    Dir.mktmpdir('tofu-apply-hash-mismatch') do |dir|
      install_fake_tofu(dir)
      install_plan_guard(dir)
      write_plan_bundle(dir, plan_id: 'plan-42')
      _, stderr, status = run_command(template.fetch('command'), dir,
                                       'approved_plan_id' => 'plan-42',
                                       'approved_plan_hash' => ('0' * 64))

      refute status.success?
      assert_match(/approved plan/i, stderr)
      refute File.exist?(File.join(dir, 'apply.called'))
    end
  end

  def test_tofu_apply_binds_the_approved_id_and_hash_before_apply
    template = YAML.load_file(File.join(TEMPLATE_DIR, 'tofu-apply-approved.yaml'))

    Dir.mktmpdir('tofu-apply-success') do |dir|
      install_fake_tofu(dir)
      install_plan_guard(dir)
      write_plan_bundle(dir, plan_id: 'plan-42')
      hash = plan_hash(dir)
      stdout, stderr, status = run_command(template.fetch('command'), dir,
                                            'approved_plan_id' => 'plan-42',
                                            'approved_plan_hash' => hash)

      assert status.success?, "apply command failed: #{stdout}\n#{stderr}"
      assert File.exist?(File.join(dir, 'apply.called'))
      binding_path = File.join(dir, 'artifacts/vm100-approved-plan.json')
      assert File.exist?(binding_path), 'missing approved-plan binding artifact'
      if File.exist?(binding_path)
        binding = JSON.parse(File.read(binding_path))
        assert_equal 'plan-42', binding.fetch('approved_plan_id')
        assert_equal hash, binding.fetch('approved_plan_hash')
      end

      stdout, stderr, status = run_command(template.fetch('post_check').fetch('command'), dir)
      assert status.success?, "post-check failed: #{stdout}\n#{stderr}"
      assert_path_with_content(dir, 'artifacts/vm100-post-apply.txt')
    end
  end

  private

  PLAN_JSON = {
    'format_version' => '1.2',
    'resource_changes' => [{
      'address' => 'proxmox_virtual_environment_vm.vm100',
      'mode' => 'managed',
      'change' => {
        'actions' => ['no-op'],
        'after' => {'vm_id' => 100, 'node_name' => 'pve'},
        'importing' => {'id' => 'pve/100'}
      }
    }]
  }.freeze

  def install_fake_tofu(dir)
    bin = File.join(dir, 'bin')
    FileUtils.mkdir_p(bin)
    path = File.join(bin, 'tofu')
    File.write(path, <<~'SH')
      #!/bin/sh
      set -eu
      mode=
      output=
      json=false
      detailed=false
      for argument in "$@"; do
        case "$argument" in
          plan) mode=plan ;;
          show) mode=show ;;
          apply) mode=apply ;;
          -out=*) output=${argument#-out=} ;;
          -json) json=true ;;
          -detailed-exitcode) detailed=true ;;
        esac
      done
      case "$mode" in
        plan)
          if [ "$detailed" = true ]; then
            printf '%s\n' "${TOFU_POST_PLAN_TEXT:-No changes after apply}"
            exit "${TOFU_POST_PLAN_EXIT:-0}"
          fi
          mkdir -p "$(dirname "$output")"
          printf '%s' 'binary-plan' > "$output"
          ;;
        show)
          if [ "$json" = true ]; then
            printf '%s\n' "$TOFU_PLAN_JSON"
          else
            printf '%s\n' "$TOFU_PLAN_TEXT"
          fi
          ;;
        apply)
          : > "$TOFU_APPLY_LOG"
          ;;
        *)
          exit 99
          ;;
      esac
    SH
    FileUtils.chmod(0o755, path)
  end

  def install_plan_guard(dir)
    destination = File.join(dir, 'automation/scripts/check-vm100-plan.py')
    FileUtils.mkdir_p(File.dirname(destination))
    FileUtils.cp(File.join(ROOT, '..', 'scripts/check-vm100-plan.py'), destination)
  end

  def install_route_publish_fixture(dir)
    %w[
      automation/routes/catalog.yml
      automation/routes/schemas/route.schema.json
      automation/scripts/render-routes.py
      automation/scripts/validate-runtime-policy.rb
      automation/policies/active-runtime.yaml
      automation/policies/retired-runtime.yaml
    ].each do |relative_path|
      source = File.join(File.expand_path('../..', ROOT), relative_path)
      destination = File.join(dir, relative_path)
      FileUtils.mkdir_p(File.dirname(destination))
      FileUtils.cp(source, destination)
    end
  end

  def write_plan_bundle(dir, plan_id:)
    artifacts = File.join(dir, 'artifacts')
    FileUtils.mkdir_p(artifacts)
    File.binwrite(File.join(artifacts, 'vm100.tfplan'), 'binary-plan')
    File.write(File.join(artifacts, 'vm100.plan.txt'), "No changes\n")
    File.write(File.join(artifacts, 'vm100.plan.json'), JSON.generate(PLAN_JSON) + "\n")
    hash = plan_hash(dir)
    File.write(File.join(artifacts, 'vm100.plan.sha256'), "#{hash}\n")
    File.write(File.join(artifacts, 'vm100.plan.manifest.json'), JSON.generate(
      'plan_id' => plan_id,
      'plan_sha256' => hash,
      'binary_artifact' => 'artifacts/vm100.tfplan',
      'text_artifact' => 'artifacts/vm100.plan.txt',
      'json_artifact' => 'artifacts/vm100.plan.json'
    ) + "\n")
  end

  def plan_hash(dir)
    Digest::SHA256.file(File.join(dir, 'artifacts/vm100.tfplan')).hexdigest
  end

  def run_command(command, dir, extra_env = {})
    env = {
      'PATH' => "#{File.join(dir, 'bin')}:#{ENV.fetch('PATH')}",
      'TOFU_PLAN_JSON' => JSON.generate(PLAN_JSON),
      'TOFU_PLAN_TEXT' => 'No changes',
      'TOFU_APPLY_LOG' => File.join(dir, 'apply.called')
    }.merge(extra_env)
    Open3.capture3(env, 'sh', '-c', command, chdir: dir)
  end

  def assert_path_with_content(dir, relative_path)
    path = File.join(dir, relative_path)
    assert File.file?(path), "missing artifact #{relative_path}"
    assert_operator File.size(path), :>, 0, "empty artifact #{relative_path}"
  end
end

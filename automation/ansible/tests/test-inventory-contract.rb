#!/usr/bin/env ruby
# frozen_string_literal: true

require 'minitest/autorun'
require 'yaml'

class AnsibleInventoryContractTest < Minitest::Test
  ROOT = File.expand_path('..', __dir__)
  INVENTORY = File.join(ROOT, 'inventories/production/hosts.yml')
  GROUP_VARS = File.join(ROOT, 'inventories/production/group_vars')

  def test_production_inventory_has_only_active_host_roles
    data = YAML.load_file(INVENTORY)
    groups = data.fetch('all').fetch('children')
    assert_equal %w[gateway pi5_manager vm100_worker].sort, groups.keys.sort
    refute_match(/k8s|kube|101|102/i, data.to_yaml)
    assert_equal ['vps-gateway'], groups.fetch('gateway').fetch('hosts').keys
    assert_equal ['pi5'], groups.fetch('pi5_manager').fetch('hosts').keys
    assert_equal ['vm100'], groups.fetch('vm100_worker').fetch('hosts').keys
  end

  def test_host_transport_has_no_application_endpoint_or_secret
    text = File.read(INVENTORY)
    refute_match(/password|token|secret|private_key/i, text)
    refute_match(/postgres|redis|rustfs|docker\.io|registry\./i, text)
  end

  def test_audit_playbook_is_read_only
    path = File.join(ROOT, 'playbooks/audit.yml')
    assert File.file?(path)
    text = File.read(path)
    assert_match(/gather_facts:\s*true/, text)
    assert_operator text.scan(/changed_when:\s*false/).length, :>=, 3
    refute_match(/service:\s*.*state:\s*(started|restarted)|docker_service|systemd:/i, text)
  end

  def test_roles_have_check_mode_safe_entrypoints
    %w[base docker swarm ssh_hardening logging swap].each do |role|
      path = File.join(ROOT, "roles/#{role}/tasks/main.yml")
      assert File.file?(path), "missing role #{role}"
      assert_match(/---/, File.read(path), "#{role} should be YAML")
    end
  end

  def test_audit_commands_run_in_check_mode_and_do_not_hide_errors
    %w[audit backup-audit].each do |name|
      tasks = YAML.load_file(File.join(ROOT, "playbooks/#{name}.yml")).first.fetch('tasks')
      tasks.select { |task| task.key?('ansible.builtin.command') }.each do |task|
        assert_equal false, task['check_mode'], task['name']
        refute_equal false, task['failed_when'], task['name']
        assert task.fetch('ansible.builtin.command').fetch('argv').all? { |arg| arg.is_a?(String) }, task['name']
      end
      refute tasks.any? { |task| task.key?('ansible.builtin.shell') }
    end
  end
end

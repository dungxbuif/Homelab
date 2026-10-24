# Semaphore design specs (not live)

The YAML files in this directory are design-only contracts. They are **not**
Semaphore templates: Semaphore Community never reads them, they are not API
import payloads, and nothing here is created by a `bootstrap-*.mjs` script. The
approval gates, `execution_image` selection and role restrictions they describe
cannot be enforced by Semaphore Community (see
[the executor compatibility decision](../../../docs/deployments/semaphore-executor-compatibility-2026-10-14.md)).

`app-deploy` and `rollback` additionally reference executor scripts
(`deploy-service`, `smoke-service`, `rollback-service`) that do not exist.

Live templates are described in `../templates/` and created by the bootstrap
scripts in `..`. Specs are validated for shape by
`../tests/test-template-contract.rb` only. Promote a spec by implementing its
executor, adding a bootstrap script and tests, and moving it back to `templates/`.

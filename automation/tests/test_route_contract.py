#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation/scripts/render-routes.py"
CATALOG = ROOT / "automation/routes/catalog.yml"

spec = importlib.util.spec_from_file_location("render_routes", SCRIPT)
render_routes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(render_routes)


class RouteContractTest(unittest.TestCase):
    def test_catalog_renders_without_forbidden_backends(self):
        catalog = render_routes.load_catalog(CATALOG)
        render_routes.validate_catalog(catalog)
        rendered = render_routes.render(catalog)
        self.assertEqual(set(rendered["http"]["routers"]), set(rendered["http"]["services"]))
        self.assertIn("lan-only", rendered["http"]["routers"]["pgadmin"]["middlewares"])
        self.assertEqual(
            rendered["http"]["services"]["llm"]["loadBalancer"]["servers"][0]["url"],
            "http://103.82.21.202:18123",
        )

    def test_current_router_set_and_observed_tunnel_are_present(self):
        catalog = render_routes.load_catalog(CATALOG)
        routes = {route['id']: route for route in catalog['routes']}
        self.assertEqual(len(routes), 24)
        self.assertEqual(routes['llm']['backend']['kind'], 'tunnel')
        for route in ('semaphore', 'kubekosh'):
            self.assertEqual(routes[route]['exposure'], 'lan')
        self.assertEqual(routes['k8s-syntax']['backend']['url'], 'http://tasks.k8s-syntax:80')

    def test_duplicate_host_without_custom_rule_is_rejected(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog["routes"] = [catalog["routes"][0], dict(catalog["routes"][0], id="duplicate")]
        with self.assertRaises(ValueError):
            render_routes.validate_catalog(catalog)

    def test_render_is_deterministic(self):
        catalog = render_routes.load_catalog(CATALOG)
        self.assertEqual(render_routes.render(catalog), render_routes.render(catalog))

    def test_catalog_matches_published_schema(self):
        schema = json.loads((ROOT / 'automation/routes/schemas/route.schema.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(render_routes.load_catalog(CATALOG))

    def test_internal_routes_are_not_published(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog['routes'][0]['exposure'] = 'internal'
        rendered = render_routes.render(catalog)
        self.assertNotIn('homepage', rendered['http']['routers'])
        self.assertNotIn('homepage', rendered['http']['services'])

    def test_netbird_requires_dedicated_private_allowlist(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog['routes'][0]['exposure'] = 'netbird'
        with self.assertRaises(ValueError):
            render_routes.render(catalog)
        catalog['middlewares']['netbird-only'] = {'ipAllowList': {'sourceRange': ['100.100.0.0/16']}}
        router = render_routes.render(catalog)['http']['routers']['homepage']
        self.assertIn('netbird-only', router['middlewares'])

    def test_invalid_private_policies_and_public_semaphore_are_rejected(self):
        for value in [[], ['0.0.0.0/0'], ['::/0'], ['1.2.3.0/24'], ['bad-cidr'], [167772160]]:
            with self.subTest(value=value):
                catalog = render_routes.load_catalog(CATALOG)
                catalog['middlewares']['lan-only'] = {'ipAllowList': {'sourceRange': value}}
                with self.assertRaises(ValueError):
                    render_routes.render(catalog)
        catalog = render_routes.load_catalog(CATALOG)
        next(r for r in catalog['routes'] if r['id'] == 'semaphore')['exposure'] = 'public'
        with self.assertRaises(ValueError):
            render_routes.render(catalog)

    def test_malformed_allowlist_fails_with_validation_error(self):
        for value in [None, [], 'bad']:
            with self.subTest(value=value):
                catalog = render_routes.load_catalog(CATALOG)
                catalog['middlewares']['lan-only'] = {'ipAllowList': value}
                with self.assertRaises(ValueError):
                    render_routes.render(catalog)

    def test_invalid_hostname_cannot_inject_router_rule(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog['routes'][0]['hostnames'] = ['x`) || HostRegexp(`.*']
        with self.assertRaises(ValueError):
            render_routes.render(catalog)

    def test_private_gate_cannot_trust_route_rewritten_forwarded_headers(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog['middlewares']['rewrite-client'] = {'headers': {'customRequestHeaders': {'X-Forwarded-For': '10.10.0.1'}}}
        route = next(r for r in catalog['routes'] if r['id'] == 'semaphore')
        route['middlewares'] = ['rewrite-client']
        catalog['middlewares']['lan-only']['ipAllowList']['ipStrategy'] = {'depth': 1}
        with self.assertRaises(ValueError):
            render_routes.render(catalog)
        del catalog['middlewares']['lan-only']['ipAllowList']['ipStrategy']
        rendered = render_routes.render(catalog)
        self.assertEqual(rendered['http']['routers']['semaphore']['middlewares'], ['lan-only', 'rewrite-client'])

    def test_private_middleware_cannot_combine_other_behaviors(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog['middlewares']['lan-only']['headers'] = {}
        with self.assertRaises(ValueError):
            render_routes.render(catalog)


if __name__ == "__main__":
    unittest.main()

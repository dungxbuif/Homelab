#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


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
            "http://10.10.0.6:1234",
        )

    def test_duplicate_host_without_custom_rule_is_rejected(self):
        catalog = render_routes.load_catalog(CATALOG)
        catalog["routes"] = [catalog["routes"][0], dict(catalog["routes"][0], id="duplicate")]
        with self.assertRaises(ValueError):
            render_routes.validate_catalog(catalog)

    def test_render_is_deterministic(self):
        catalog = render_routes.load_catalog(CATALOG)
        self.assertEqual(render_routes.render(catalog), render_routes.render(catalog))


if __name__ == "__main__":
    unittest.main()

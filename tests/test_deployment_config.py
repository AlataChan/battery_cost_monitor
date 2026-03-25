import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DeploymentConfigTests(unittest.TestCase):
    def test_docker_compose_exposes_required_api_environment(self):
        compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("API_KEY=${API_KEY:-}", compose)
        self.assertIn("SNAPSHOT_CACHE_TTL=${SNAPSHOT_CACHE_TTL:-300}", compose)
        self.assertIn("CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:5001}", compose)

    def test_nginx_conf_restricts_surface_and_rate_limits_api(self):
        nginx_conf = (PROJECT_ROOT / "nginx.conf").read_text(encoding="utf-8")

        self.assertIn("limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;", nginx_conf)
        self.assertIn("if ($http_x_api_key = \"\") { return 401; }", nginx_conf)
        self.assertIn("limit_req zone=api burst=20 nodelay;", nginx_conf)
        self.assertIn("location /output/", nginx_conf)
        self.assertIn("deny all;", nginx_conf)
        self.assertIn("location = /api/status", nginx_conf)


if __name__ == "__main__":
    unittest.main()

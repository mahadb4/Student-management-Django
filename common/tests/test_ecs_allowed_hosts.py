import importlib.util
import io
import json
import os
import urllib.error
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

METADATA_URI = "http://169.254.170.2/v4/test-task"
TASK_IP = "10.0.1.23"


def _load_settings(environ, urlopen):
    # Executes settings.py as a throwaway module so the live settings are untouched
    spec = importlib.util.spec_from_file_location(
        "ecs_settings_under_test", settings.BASE_DIR / "student_ms" / "settings.py"
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, environ), mock.patch("urllib.request.urlopen", urlopen):
        if "ECS_CONTAINER_METADATA_URI_V4" not in environ:
            os.environ.pop("ECS_CONTAINER_METADATA_URI_V4", None)
        spec.loader.exec_module(module)
    return module


def _metadata_response(payload):
    return mock.Mock(return_value=io.BytesIO(json.dumps(payload).encode()))


class EcsAllowedHostsTests(SimpleTestCase):
    def setUp(self):
        self.urlopen_outside_ecs = mock.Mock()
        self.baseline_hosts = _load_settings({}, self.urlopen_outside_ecs).ALLOWED_HOSTS

    def test_outside_ecs_allowed_hosts_unchanged_and_no_lookup(self):
        self.urlopen_outside_ecs.assert_not_called()
        # The test runner appends "testserver" to the live setting
        live_hosts = [host for host in settings.ALLOWED_HOSTS if host != "testserver"]
        self.assertEqual(self.baseline_hosts, live_hosts)
        self.assertNotIn(TASK_IP, self.baseline_hosts)

    def test_task_ip_from_metadata_is_added(self):
        urlopen = _metadata_response(
            {"Containers": [{"Networks": [{"NetworkMode": "awsvpc", "IPv4Addresses": [TASK_IP]}]}]}
        )

        hosts = _load_settings({"ECS_CONTAINER_METADATA_URI_V4": METADATA_URI}, urlopen).ALLOWED_HOSTS

        urlopen.assert_called_once_with(f"{METADATA_URI}/task", timeout=2)
        self.assertEqual(hosts, self.baseline_hosts + [TASK_IP])

    def test_metadata_without_networks_adds_nothing(self):
        urlopen = _metadata_response({"Containers": [{"Name": "web"}]})

        hosts = _load_settings({"ECS_CONTAINER_METADATA_URI_V4": METADATA_URI}, urlopen).ALLOWED_HOSTS

        self.assertEqual(hosts, self.baseline_hosts)

    def test_lookup_failure_does_not_crash_settings(self):
        urlopen = mock.Mock(side_effect=urllib.error.URLError("unreachable"))

        hosts = _load_settings({"ECS_CONTAINER_METADATA_URI_V4": METADATA_URI}, urlopen).ALLOWED_HOSTS

        urlopen.assert_called_once()
        self.assertEqual(hosts, self.baseline_hosts)

    def test_invalid_metadata_json_does_not_crash_settings(self):
        urlopen = mock.Mock(return_value=io.BytesIO(b"not json"))

        hosts = _load_settings({"ECS_CONTAINER_METADATA_URI_V4": METADATA_URI}, urlopen).ALLOWED_HOSTS

        self.assertEqual(hosts, self.baseline_hosts)

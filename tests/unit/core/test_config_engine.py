# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for CascadingConfigEngine and variable interpolation."""

from unittest.mock import patch

from artemis.config.core import CascadingConfigEngine, interpolate_config_value


def test_interpolate_env_variables():
    """Verify ${env:KEY} expressions are properly interpolated."""
    with patch.dict("os.environ", {"TEST_KEY": "secret_123"}):
        result = interpolate_config_value("Bearer ${env:TEST_KEY}")
        assert result == "Bearer secret_123"

        default_result = interpolate_config_value("${env:MISSING_KEY:-fallback_val}")
        assert default_result == "fallback_val"


def test_interpolate_path_variables():
    """Verify ${path:KEY} expressions resolve system standard paths."""
    result = interpolate_config_value("${path:temp_dir}/screenshots")
    assert "/screenshots" in result or "\\screenshots" in result


def test_cascading_config_merge():
    """Verify CLI overrides take precedence in CascadingConfigEngine."""
    engine = CascadingConfigEngine()
    merged = engine.load_raw_config(cli_overrides={"default": {"model": "gemini-test-custom"}})
    assert merged.get("default", {}).get("model") == "gemini-test-custom"


def test_parse_llm_config_interpolates_env(tmp_path):
    """Verify ${env:...} in artemis.jsonc switches the LLM model per run."""
    from artemis.config import llm as llm_config

    config_file = tmp_path / "artemis.jsonc"
    config_file.write_text(
        '{"default": {"provider": "${env:T_PROVIDER:-openai}", "model": "${env:T_MODEL:-m1}",'
        ' "fallback": {"provider": "google", "model": "g1"}}}'
    )
    with patch.object(llm_config, "get_config_path", return_value=config_file):
        assert str(llm_config.parse_llm_config().operator.model) == "m1"
        with patch.dict("os.environ", {"T_PROVIDER": "google", "T_MODEL": "m2"}):
            cfg = llm_config.parse_llm_config()
            assert (cfg.operator.provider, cfg.operator.model) == ("google", "m2")

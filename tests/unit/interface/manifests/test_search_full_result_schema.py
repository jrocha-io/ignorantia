"""Schema-level tests for ``search_full_result.schema.json``."""

from __future__ import annotations

import pytest
from jsonschema.exceptions import ValidationError

from ignorantia.interface.manifests import validate_manifest


def _valid_payload() -> dict[str, object]:
    return {
        "per_source": [
            {
                "source": "arxiv",
                "source_tier": "tier1",
                "method": "real",
                "total_results": 10,
                "items": [
                    {
                        "title": "Paper A",
                        "source_tier": "tier1",
                        "authors": ["Silva, J."],
                        "year": 2024,
                        "doi": "10.1234/a",
                        "issn": None,
                        "isbn": None,
                        "venue": "Journal",
                        "language": "en",
                        "is_oa": True,
                        "url": "https://example.org/a",
                        "url_for_pdf": None,
                        "abstract": "",
                        "publication_type": None,
                    }
                ],
            }
        ],
        "deduplicated_items": [
            {
                "title": "Paper A",
                "source_tier": "tier1",
                "authors": ["Silva, J."],
                "year": 2024,
                "doi": "10.1234/a",
                "issn": None,
                "isbn": None,
                "venue": "Journal",
                "language": "en",
                "is_oa": True,
                "url": "https://example.org/a",
                "url_for_pdf": None,
                "abstract": "",
                "publication_type": None,
            }
        ],
    }


class TestSearchFullResultSchema:
    def test_full_payload_passes(self) -> None:
        validate_manifest("search_full_result", _valid_payload())

    def test_empty_per_source_and_items_passes(self) -> None:
        validate_manifest(
            "search_full_result",
            {"per_source": [], "deduplicated_items": []},
        )

    def test_missing_per_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            validate_manifest(
                "search_full_result",
                {"deduplicated_items": []},
            )

    def test_unknown_method_in_per_source_rejected(self) -> None:
        payload = _valid_payload()
        payload["per_source"][0]["method"] = "weird"  # type: ignore[index]
        with pytest.raises(ValidationError):
            validate_manifest("search_full_result", payload)

    def test_unknown_source_tier_rejected(self) -> None:
        payload = _valid_payload()
        payload["deduplicated_items"][0]["source_tier"] = "tier99"  # type: ignore[index]
        with pytest.raises(ValidationError):
            validate_manifest("search_full_result", payload)

    def test_extra_top_level_field_rejected(self) -> None:
        payload = _valid_payload()
        payload["stowaway"] = "should fail"
        with pytest.raises(ValidationError):
            validate_manifest("search_full_result", payload)

    def test_negative_total_results_rejected(self) -> None:
        payload = _valid_payload()
        payload["per_source"][0]["total_results"] = -1  # type: ignore[index]
        with pytest.raises(ValidationError):
            validate_manifest("search_full_result", payload)

    def test_known_manifests_includes_search_full_result(self) -> None:
        from ignorantia.interface.manifests import known_manifests

        assert "search_full_result" in known_manifests()

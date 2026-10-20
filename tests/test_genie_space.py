import json
import re

import pytest

from genie.build_space import GOLD_COLUMNS, TABLE_NAME, build_create_request, build_serialized_space

HEX_ID = re.compile(r"^[0-9a-f]{32}$")


def _id_items(space):
    instructions = space["instructions"]
    snippets = instructions["sql_snippets"]
    return {
        "sample_questions": space["config"]["sample_questions"],
        "benchmarks": space["benchmarks"]["questions"],
        "example_question_sqls": instructions["example_question_sqls"],
        "text_instructions": instructions["text_instructions"],
        "measures": snippets["measures"],
        "filters": snippets["filters"],
    }


def test_space_is_deterministic_and_targets_the_forecast_table():
    space = build_serialized_space("main", "demo_factory")

    assert space == build_serialized_space("main", "demo_factory")
    assert space["version"] == 2
    assert [t["identifier"] for t in space["data_sources"]["tables"]] == [
        f"main.demo_factory.{TABLE_NAME}"
    ]


def test_ids_are_hex_sorted_and_unique_where_the_api_requires():
    groups = _id_items(build_serialized_space("main", "demo_factory"))

    for name, items in groups.items():
        ids = [item["id"] for item in items]
        assert all(HEX_ID.fullmatch(i) for i in ids), name
        assert ids == sorted(ids), f"{name} must be sorted by id"

    question_ids = [i["id"] for i in groups["sample_questions"] + groups["benchmarks"]]
    instruction_ids = [
        i["id"]
        for key in ("example_question_sqls", "text_instructions", "measures", "filters")
        for i in groups[key]
    ]
    assert len(question_ids) == len(set(question_ids))
    assert len(instruction_ids) == len(set(instruction_ids))
    assert len(groups["text_instructions"]) <= 1


def test_column_configs_are_sorted_and_match_gold_columns():
    table = build_serialized_space("main", "demo_factory")["data_sources"]["tables"][0]
    names = [c["column_name"] for c in table["column_configs"]]

    assert names == sorted(names)
    assert set(names) <= set(GOLD_COLUMNS)


def test_snippet_columns_are_qualified():
    snippets = build_serialized_space("main", "demo_factory")["instructions"]["sql_snippets"]

    for snippet in snippets["measures"] + snippets["filters"]:
        sql = " ".join(snippet["sql"])
        for column in GOLD_COLUMNS:
            for match in re.finditer(rf"(?<![\w.]){column}\b", sql):
                pytest.fail(f"Unqualified column {column!r} in {snippet['display_name']}")


def test_text_fields_are_arrays():
    space = build_serialized_space("main", "demo_factory")

    for item in space["config"]["sample_questions"] + space["instructions"]["example_question_sqls"]:
        assert isinstance(item["question"], list)
    for item in space["instructions"]["example_question_sqls"]:
        assert isinstance(item["sql"], list)
    for item in space["benchmarks"]["questions"]:
        assert item["answer"][0]["format"] == "SQL"


def test_create_request_embeds_space_as_string():
    request = build_create_request("main", "demo_factory", "abc123", "/Workspace/Users/x/genie")

    assert request["warehouse_id"] == "abc123"
    assert json.loads(request["serialized_space"]) == build_serialized_space("main", "demo_factory")


def test_rejects_unsafe_identifiers():
    with pytest.raises(ValueError):
        build_serialized_space("main; DROP", "demo_factory")

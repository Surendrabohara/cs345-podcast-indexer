from indexer.search import search_segments

EPISODES = [
    {
        "id": "a1", "title": "Glacier basics",
        "segments": [
            {"start": 0, "end": 30, "text": "Glacier melt is speeding up.", "people": ["Maya Ortiz"], "topics": ["glacier melt"]},
            {"start": 30, "end": 60, "text": "Villages depend on river water.", "people": [], "topics": ["water supply"]},
        ],
    },
    {
        "id": "b2", "title": "School clubs",
        "segments": [
            {"start": 0, "end": 40, "text": "Science clubs build small satellites.", "people": ["Aiden Cole"], "topics": ["science clubs"]},
        ],
    },
]


def test_text_search_finds_matching_segment():
    out = search_segments(EPISODES, q="glacier")
    assert [h["episode_id"] for h in out["results"]] == ["a1"]
    assert out["results"][0]["start_sec"] == 0


def test_person_filter():
    out = search_segments(EPISODES, q="", person="aiden cole")
    assert [h["episode_id"] for h in out["results"]] == ["b2"]


def test_topic_filter_and_text_together():
    out = search_segments(EPISODES, q="water", topic="water supply")
    assert len(out["results"]) == 1


def test_no_match_gives_empty_list_and_a_latency():
    out = search_segments(EPISODES, q="volcano")
    assert out["results"] == []
    assert out["latency_ms"] >= 0


def test_person_name_in_query_matches_people_field():
    out = search_segments(EPISODES, q="Maya")
    assert out["results"][0]["episode_id"] == "a1"

async def test_player_stats_empty(client, session):
    resp = await client.get("/stats/players?period=all")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_team_stats_empty(client, session):
    resp = await client.get("/stats/teams?period=all")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_player_stats_with_data(client, session, fake_redis):
    from tests.test_answers import full_game_setup
    _, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    resp = await client.get("/stats/players?period=all")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["total_points"] >= 1


async def test_team_stats_with_data(client, session, fake_redis):
    from tests.test_answers import full_game_setup
    _, player_headers, game_id, gq_id, _ = await full_game_setup(session, client)
    await client.post(
        f"/games/{game_id}/questions/{gq_id}/answer",
        json={"chosen_option_index": 0},
        headers=player_headers,
    )
    resp = await client.get("/stats/teams?period=all")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

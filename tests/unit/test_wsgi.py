def test_wsgi_application_loads() -> None:
    from hw_radar.wsgi import application

    assert application is not None

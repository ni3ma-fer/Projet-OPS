from gazette.__main__ import main


def test_main_affiche_ok(capsys):
    main()
    assert "gazette: ok" in capsys.readouterr().out

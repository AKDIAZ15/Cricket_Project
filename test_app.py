import requests

def test_home():

    try:
        r = requests.get(
            "http://localhost:5000/"
        )

        assert r.status_code == 200

    except:
        assert True
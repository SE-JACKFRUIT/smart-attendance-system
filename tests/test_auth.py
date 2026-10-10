from conftest import login, make_admin


def test_first_run_redirects_to_setup(client):
    r = client.get("/")
    assert r.status_code == 302 and "/setup" in r.headers["Location"]


def test_setup_creates_admin_and_login_works(client):
    make_admin(client)
    assert b"Welcome, boss" in login(client, "boss", "secret1").data


def test_setup_blocked_password_mismatch(client):
    client.post("/setup", data={"username": "a", "password": "secret1", "confirm": "different"})
    assert "/setup" in client.get("/").headers["Location"]  # still no admin


def test_wrong_password_rejected(client):
    make_admin(client)
    assert b"Invalid username or password" in login(client, "boss", "nope").data


def test_no_default_accounts(client):
    make_admin(client)
    assert b"Invalid" in login(client, "admin", "admin123").data
    assert b"Invalid" in login(client, "faculty", "faculty123").data


def test_register_needs_admin_authorization(admin):
    admin.get("/logout")
    r = admin.post("/register", data={"role": "Faculty", "username": "fac", "password": "abcdef",
                                      "confirm": "abcdef", "auth_username": "boss",
                                      "auth_password": "WRONG"}, follow_redirects=True)
    assert b"wrong" in r.data
    assert b"Invalid" in login(admin, "fac", "abcdef").data


def test_register_creates_faculty(admin):
    admin.get("/logout")
    admin.post("/register", data={"role": "Faculty", "username": "fac", "password": "abcdef",
                                  "confirm": "abcdef", "auth_username": "boss",
                                  "auth_password": "secret1"})
    assert b"Welcome, fac (Faculty)" in login(admin, "fac", "abcdef").data


def test_register_short_password_rejected(admin):
    r = admin.post("/register", data={"role": "Faculty", "username": "fac", "password": "abc",
                                      "confirm": "abc", "auth_username": "boss",
                                      "auth_password": "secret1"}, follow_redirects=True)
    assert b"at least 6" in r.data


def test_login_required_for_dashboard(client):
    make_admin(client)
    assert "/login" in client.get("/dashboard").headers["Location"]


def test_logout(admin):
    assert b"Logged out" in admin.get("/logout", follow_redirects=True).data

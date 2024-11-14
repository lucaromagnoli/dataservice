import nox
import nox_poetry

nox.options.sessions = ["tests"]
nox.options.error_on_missing_interpreters = True


@nox_poetry.session
def tests(session):
    session.install(".")
    session.run(
        "pytest",
        "tests/",
        "-v",
        "--cov=dataservice/",
        "--ignore=tests/integration/test_pw_extra_http_headers.py",
        external=True,
    )

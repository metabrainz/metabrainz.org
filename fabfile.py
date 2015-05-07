from __future__ import with_statement
from fabric.api import local
from fabric.colors import yellow, green
from metabrainz import create_app, cache
from metabrainz.model.utils import init_postgres


def git_pull():
    local("git pull origin")
    print(green("Updated local code.", bold=True))


def install_requirements():
    local("pip install -r requirements.txt")
    print(green("Installed requirements.", bold=True))


def compile_styling():
    """Compile styles.less into styles.css.

    This command requires Less (CSS pre-processor). More information about it can be
    found at http://lesscss.org/.
    """
    style_path = "metabrainz/static/css/"
    local("lessc --clean-css %smain.less > %smain.css" % (style_path, style_path))
    print(green("Style sheets have been compiled successfully.", bold=True))


def clear_memcached():
    with create_app().app_context():
        cache.flush_all()
    print(green("Flushed everything from memcached.", bold=True))


def deploy():
    git_pull()
    install_requirements()
    compile_styling()
    clear_memcached()


def test(init_db=True, coverage=True):
    """Run all tests.

    It will also initialize the test database and create code coverage report, unless
    specified otherwise. Database that will be used for tests can be specified in the
    application config file. See `TEST_SQLALCHEMY_DATABASE_URI` variable.

    Code coverage report will be located in cover/index.html file.
    """
    if init_db:
        # Creating database-related stuff
        init_postgres(create_app().config['TEST_SQLALCHEMY_DATABASE_URI'])

    if coverage:
        local("nosetests --exe --with-coverage --cover-package=metabrainz --cover-erase --cover-html")
        print(yellow("Coverage report can be found in cover/index.html file.", bold=True))
    else:
        local("nosetests --exe")

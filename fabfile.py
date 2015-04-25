from __future__ import with_statement
from fabric.api import local
from fabric.colors import green
from fabric.colors import yellow
from metabrainz import create_app
from metabrainz.model.utils import init_postgres


def compile_styling():
    """Compile styles.less into styles.css.

    This command requires Less (CSS pre-processor). More information about it can be
    found at http://lesscss.org/.
    """
    style_path = "metabrainz/static/css/"
    local("lessc --clean-css %smain.less > %smain.css" % (style_path, style_path))
    print(green("Style sheets have been compiled successfully.", bold=True))


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

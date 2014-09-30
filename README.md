# metabrainz.org

Modern version of [MetaBrainz Foundation](http://metabrainz.org/) website.

## Development

Before starting the application copy `config.py.example` into `config.py` and tweak the configuration.

The easiest way to set up a development environment is to use [Vagrant](https://www.vagrantup.com/).
This command will create and configure virtual machine that you will be able to use for development:

    $ vagrant up

After VM is created and running, access it via SSH and start the application: 

    $ vagrant ssh
    $ cd /vagrant
    $ python run.py

Web server should be accessible at http://localhost:5000/.

### Testing

We use [nose](http://readthedocs.org/docs/nose/) package to run test cases:

    $ nosetests

If you want to take a look at code coverage use:

    $ nosetests --with-coverage --cover-package=metabrainz --cover-erase --cover-html

This will produce a coverage report in HTML format. It will be located in cover/index.html file.

## Community

If you want to discuss something, go to #musicbrainz-devel IRC channel on irc.freenode.net.
More info is available at https://wiki.musicbrainz.org/Communication.

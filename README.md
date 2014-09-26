# metabrainz.org

Modern version of [MetaBrainz Foundation](http://metabrainz.org/) website.

## Development

The easiest way to set up a development environment is to use [Vagrant](https://www.vagrantup.com/).
This command will create and configure virtual machine that you will be able to use for development:

    $ vagrant up

After VM is created and running, access it via SSH and start the application: 

    $ vagrant ssh
    $ cd /vagrant
    $ python run.py


If you want to discuss something, go to *#musicbrainz-devel* IRC channel on *irc.freenode.net*.
More info is available at https://wiki.musicbrainz.org/Communication.

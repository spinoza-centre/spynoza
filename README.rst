Spynoza
=======
Spynoza is a package for fMRI data (pre)processing developed by researchers affiliated with the `Spinoza Centre for
Neuroimaging <https://www.spinozacentre.nl/>`_. Specifically, the `Knapen lab <https://tknapen.github.io/>`
(Free University Amsterdam) and the Scholte lab (University of Amsterdam) lead the development of the package. Some of
the workflows are based on existing functionality from the `fmriprep <https://github.com/poldracklab/fmriprep>` package.

Status
------
.. image:: https://travis-ci.org/spinoza-centre/spynoza.svg?branch=develop
    :target: https://travis-ci.org/spinoza-centre/spynoza

.. image:: https://coveralls.io/repos/github/spinoza-centre/spynoza/badge.svg?branch=develop
    :target: https://coveralls.io/github/spinoza-centre/spynoza?branch=develop

Prerequisites
-------------
Spynoza uses Nipype to organize processing workflows, which in turns relies heavily on FSL and, for some
registration issues, Freesurfer.

Installation
------------
Spynoza is still (very much) in development, but if you want to try it out, you can install the develop branch by::

    $ pip install git+https://github.com/spinoza-centre/spynoza.git@develop

Contributing: setup and git workflow
------------------------------------
For contributors (within the Spinoza centre organization on Github), follow these guidelines to contribute to the repo.
First, `cd` to a folder where you want the spynoza git to be setup.
To clone the repo into that dir and run::

    $ git clone git@github.com:spinoza-center/spynoza.git`

This cloned the master branch into the repo. We also need the develop branch.
To create a new branch that syncs with the upstream develop branch run
(no need to run additional pull)::

    $ git checkout --track origin/develop

This ensures that when you run `git pull` from the develop branch,
it syncs with the origin/develop branch (instead of origin/master).

Now we'll want to create our own feature branch to start working on our
contribution. We can branch off of develop by running::

    $ git checkout -b my_feature develop

To get an overview of the branches we've created, run::

    $ git branch

To switch to another branch run::

    $ git checkout branch_name

When working on your feature, make sure you first switch to your feature branch.
Then, do your work, and run::

    $ git commit -am "Your message"

Make sure you have a seperate feature branch for every distinct feature you're implementing.

When your feature is finished, and you'd like to share it with your collaborators,
merge your changes in develop without a fast-forward. First switch to the develop branch::

    $ git checkout develop

Then merge your feature changes into develop::

    $ git merge --no-ff my_feature

Now push changes to the server::

    $ git push origin develop
    $ git push origin my_feature

You are now free to delete your own feature branch if you wish using::

    $ git branch -d my_feature

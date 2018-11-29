# Oozie dbd testing

## Introduction
This repository contains a Jenkins job that runs integration tests on Oozie using
[dbd](https://github.com/d-becker/dbd).

## Usage
This section describes how to set up a Jenkins job to test Oozie.

### Setting up the Jenkins job
1. Fork this repository. You can use this respository directly without forking it if you do not want to change the test
   configurations, but for example to set the versions of the components to use, you will need to modify or add new
   files to the `configurations` directory.
1. On the Jenkins WebUI, click `New Item`. Enter a name for the project and select `Multibranch Pipeline` from the
   list. Click OK to go to the next step.
1. On the next screen, go to `Branch Sources`, click `Add source` and select `Git`. Copy the URL of your fork of this
   repository to the `Project Repository` field. Save the configuration.

### Running the tests
1. On the Jenkins WebUI, choose the project you've just created.
1. On the next screen, choose the branch you'd like to use, for example `master`. Note that this does not refer to the
   Oozie branch to test, it is the branch in the Jenkins job repository.
1. Click `Build with Parameters`. The next screen shows the parameters of the Jenkins job with the default values
   pre-filled (where applicable). The parameters all have descriptions, refer to them for information on what they
   do. After setting the parameters, click `Build`. Your Jenkins job should be running.
1. After the job has finished, a test result summary is generated. You can also download the logs of the Oozie server,
   Yarn containers and the testing framework itself from the `Build Artifacts`, all bundled up in an archive.
   
### Testing a custom Oozie build
There is a hack to circumvent the Oozie building stage and use a pre-built Oozie in the tests. This may be useful when
testing this framework to save time. For this to work, though, you need access to the file system of the Jenkins
server. If you do not have it, you can try running Jenkins in a Docker container on your own machine. For information on
how to do it, see https://jenkins.io/doc/book/installing/#docker.

1. On the filesystem of the Jenkins server, go to the workspace of the project and branch for which you'd like to use a
   custom Oozie build. It may be located at `/var/jenkins_home/workspace/PROJECT_BRANCH-SOME-GENERATED-STRING`.
1. Create a symlink with the name `test_symlink_to_oozie_distro` that points to the Oozie distribution you'd like to
   use. It has to be the directory that contains the built Oozie distribution, that is, not the top-level Oozie
   directory.
   
During the build process, if the symlink with the name `test_symlink_to_oozie_distro` exists, its target is used as the
Oozie distribution. Otherwise, Oozie is built from source.

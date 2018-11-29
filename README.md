# Oozie dbd testing

## Introduction
This repository contains a Jenkins job that runs integration tests on Oozie using
[dbd](https://github.com/d-becker/dbd).

## Usage
This section describes how to set up a Jenkins job to test Oozie.

### Starting a dockerised Jenkins server
To run the Jenkins job, you need a Jenkins server. This might be a physical machine on which Jenkins is installed, but
if one of the simplest ways is to run Jenkins in a docker container on your local machine. This section explains how to
launch and configure a Jenkins server in a docker container.

For this, you need to install Docker on your computer and run the Docker daemon. You can find information about how to
do it [here](https://docs.docker.com/install/).

If the Docker daemon is running on your computer, you can start setting up the Jenkins server. We will go through the
process, but if you need more information, you can find it [here](https://jenkins.io/doc/book/installing/#docker).

The following steps guide you through the process of setting up a dockerised Jenkins server:
1. Run the following command in a terminal:

```
docker run \
	-u root \
	--rm \
	-d \
	-p 8080:8080 \
	-p 50000:50000 \
	-v jenkins-data:/var/jenkins_home \
	-v /var/run/docker.sock:/var/run/docker.sock \
	jenkinsci/blueocean
```

This will download the docker image `jenkinsci/blueocean` and run it. We will use a volume named `jenkins-data` to
persist the configuration of the Jenkins server. If you later forget your username or password and want to configure a
completely new server, delete that volume:

```
docker volume rm jenkins-data
```

1. In a browser, go to http://localhost:8080. Here you need to unlock Jenkins. To get the password, go back to your
   terminal and run

```
docker logs <container-id>
```

For example, if your container has id `eea18cb1b5d0`, run `docker logs eea18cb1b5d0`. In the logs, between the starred
stripes, you can find the password. Copy it to the field on the web page and click `Continue`.

1. On the next page, you can select which Jenkins plugins you would like to install. Choose `Install suggested
   plugins`. Wait until the plugins are installed.

1. Now you have to create the first admin user. Choose a username and a password, fill in the form and click `Save and
   continue`.

1. Next, you have to specify the Jenkins URL. Leave it to be the default, http://localhost:8080/. Click `Save and
   Finish`.

1. Jenkins needs to be restarted, click the `Restart` button.

1. Wait for Jenkins to start. You may need to refresh the page in your browser.

1. Log in with your username and password. You are ready to use Jenkins.

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

#!/bin/bash
# It is used to upload the Oozie examples to hdfs and install 
# and start the ssh server that is needed by the ssh example.


function setup_and_start_ssh_server {
    sudo apk add --update --no-cache openrc openssh
    ssh-keygen -f ~/.ssh/id_rsa -P ""
    cat ~/.ssh/id_rsa.pub > ~/.ssh/authorized_keys

    sudo rc-status
    sudo touch /run/openrc/softlevel
    sudo /etc/init.d/sshd start

    echo "SSH server running on localhost."
}

function wait_for_oozie {
    # while ! jps | grep -q EmbeddedOozieServer
    # while ! jps | grep -q -i Oozie
    # while ! bin/oozie admin -status
    while ! jps | grep -E -q 'EmbeddedOozieServer|Bootstrap'
    do
        sleep 0.5
    done

    echo "Oozie is up and running."
}

function upload_examples {
    echo "Uploading examples"
    tar -xzf oozie-examples.tar.gz
    wait_for_oozie
    hdfs dfs -put examples examples && \
    echo "Examples uploaded to hdfs."
}

setup_and_start_ssh_server
upload_examples


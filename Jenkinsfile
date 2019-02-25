String python_path(String workspace) {
    return "${workspace}/opt/python-3.7.1/bin"
}

String maven_home = '/home/jenkins/tools/maven/latest'

void cleanup() {
    sh 'if [ -e testing ]; then rm -r testing; fi'
    sh 'mkdir testing'
}

pipeline {
    agent {
        label 'Hadoop&&!H9&&!H5&&!H6'
    }

    tools {
    	jdk 'JDK 1.8 (latest)'
    }

    parameters {
        string(defaultValue: 'master',
            description: 'Oozie branch, tag or commit. In the Oozie repository, this reference will be checked out ' +
                         'before building and testing.',
            name: 'oozie_branch')
        string(defaultValue: 'configuration',
            description: 'A list of filenames in the `configurations` directory. ' +
                         'If provided, only the `BuildConfiguration`s in the list will be built.',
            name: 'configuration_files')
        string(defaultValue: 'map-reduce Fluent_JavaMain',
            description: 'The names of the example tests to be run. An empty list means all non-blacklisted tests will be run.',
            name: 'whitelist')
        string(defaultValue: 'hcatalog',
            description: 'The names of the example tests that should be skipped.',
            name: 'blacklist')
        string(defaultValue: 'Fluent_CredentialsRetrying',
            description: 'A list of fluent examples that should only be validated, not run.',
            name: 'validate_only')
        string(defaultValue: '180',
            description: 'The timeout after which running examples are killed.',
            name: 'timeout')
        string(defaultValue: '10',
            description: 'The maximal number of (regular) files that are allowed to be kept in the cache.',
            name: 'cache_size')
        booleanParam(defaultValue: false,
            description: 'Whether the script should clean up after running (cleanup before running always happens).',
            name: 'cleanup_after_run')
        booleanParam(defaultValue: false,
            description: 'Whether the script should remove the generated docker images.',
            name: 'remove_docker_images')
    }

    environment {
    	MAVEN_HOME = "${maven_home}"
        PATH = "${python_path(env.WORKSPACE)}:${python_path(env.WORKSPACE)}/bin:$JAVA_HOME/bin:${maven_home}/bin:$PATH"
    }

    stages {
        stage('check-maven') {
            steps {
                sh 'echo $PATH'
                sh 'which mvn'
	    }
	}
        stage('cleanup') {
            steps {
                cleanup()
            }
        }
        stage('clone-dbd') {
            steps {
                sh '/bin/bash -c "cd testing && git clone https://github.com/d-becker/dbd.git"'
            }
        }
	stage('build-python') {
	   steps {
	       sh "cd testing && \
	           mkdir custom_python && \
	           cd custom_python && \
	      	   wget https://www.python.org/ftp/python/3.7.1/Python-3.7.1.tgz && \
	      	   tar zxvf Python-3.7.1.tgz && \
	       	   cd Python-3.7.1 && \
	      	   ./configure --prefix=${python_path(env.WORKSPACE)} && \
              	   make && \
              	   make install"
	   }
	}
	stage('install-python-packages') {
	    steps {
                sh 'pip3 install docker pyyaml docker-compose'
	    }
	}
        stage('build-oozie') {
            steps {
                sh "scripts/build_oozie_and_symlink.sh ${params.oozie_branch} ${params.configuration_files}"
            }
        }
        stage('dbd') {
            steps {
                sh 'mkdir testing/output'

                script {
                    def script_base = "python3 scripts/test_stage.py configurations testing/output "

                    def script_build_config_files = ""
                    if (params.configuration_files.length() > 0) {
                        script_build_config_files = "-c ${params.configuration_files} "
                    }

                    def script_whitelist = ""
                    if (params.whitelist.length() > 0) {
                        script_whitelist = "-w ${params.whitelist} "
                    }

                    def script_blacklist = ""
                    if (params.blacklist.length() > 0) {
                        script_blacklist = "-b ${params.blacklist} "
                    }

                    def script_validate_only = ""
                    if (params.validate_only.length() > 0) {
                        script_validate_only = "-v ${params.validate_only} "
                    }

                    def script_timeout = ""
                    if (params.timeout.length() > 0) {
                        script_timeout = "-t ${params.timeout} "
                    }

                    def script_cache_size = "--cache_size ${params.cache_size} "

                    def script = script_base + script_build_config_files +
                                 script_whitelist + script_blacklist +
                                 script_validate_only + script_timeout + script_cache_size

                    def returnCode = sh (script: script,
                                         returnStatus: true)

                    sh 'tar czf testing/reports.tar.gz -C testing reports'

                    archiveArtifacts (artifacts: 'testing/reports.tar.gz')

                    if (returnCode != 0) {
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }
        stage('junit') {
            steps {
                junit testResults: 'testing/reports/*/report*.xml' //, allowEmptyResults: true
            }
        }
    }
    post {
        always {
            script {
                if (params.remove_docker_images) {
                    sh 'python3 scripts/remove_generated_docker_images.py testing/output'
		    sh 'docker container prune -f'
		    sh 'docker image prune -f'
                }

                if (params.cleanup_after_run) {
                    cleanup()
                }
            }
        }
    }
}
pipeline {
    agent {
        dockerfile {
            args '--mount \'type=volume,src=m2,dst=/root/.m2\''
        }
    }

    parameters {
        string(defaultValue: 'master',
               description: 'Oozie branch',
               name: 'oozie_branch')
	string(defaultValue: 'configuration',
	       description: 'BuildConfiguration files to build.',
	       name: 'configuration_files')
	string(defaultValue: 'map-reduce Fluent_JavaMain',
	       description: 'The names of the example tests to be run. An empty list means all non-blacklisted tests will be run.',
	       name: 'whitelist')
	string(defaultValue: 'hcatalog',
	       description: 'The names of the example tests that should be skipped.',
	       name: 'blacklist')
    }

    stages {
        stage('cleanup') {
            steps {
                sh 'if [ -e testing ]; then rm -r testing; fi'
                sh 'mkdir testing'
            }
        }
        stage('clone-dbd') {
            steps {
                sh '/bin/bash -c "cd testing && git clone https://github.com/d-becker/dbd.git"'
            }
        }
        stage('clone-oozie') {
            steps {
                sh '/bin/bash -c "cd testing && git clone https://github.com/apache/oozie.git"'
                sh "/bin/bash -c \"cd testing/oozie && git checkout ${params.oozie_branch}\""
            }
        }
        stage('build-oozie') {
            steps {
	        // The condition is for testing purposes -- we would like to avoid having to build Oozie when testing.
                sh '''/bin/bash -c "if [ ! -L test_symlink_to_oozie_distro ]; then cd testing/oozie \
                                        && bin/mkdistro.sh -Puber -Ptez -DskipTests \
                                        && REL_PATH=(distro/target/oozie-*-distro/oozie-*) \
                                        && echo $REL_PATH \
                                        && ln -sf "$(pwd)/$REL_PATH" ../../symlink_to_oozie_distro; \
                                     else ln -sf test_symlink_to_oozie_distro symlink_to_oozie_distro; fi"'''
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

                    def script = script_base + script_build_config_files + script_whitelist + script_blacklist

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
}
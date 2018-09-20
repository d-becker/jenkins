pipeline {
    agent { dockerfile true }

    parameters {
        string(defaultValue: 'master', description: 'Oozie branch', name: 'oozie_branch')
	string(defaultValue: 'map-reduce hive2',
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
                sh '''/bin/bash -c "if [ ! -L symlink_to_oozie_distro ]; then cd testing/oozie \
                                    && bin/mkdistro.sh -Puber -Ptez -DskipTests \
                                    && ln -s testing/oozie/distro/target/oozie-*-distro/oozie-* symlink_to_oozie_distro; fi"'''
            }
        }
        stage('dbd') {
            steps {
                sh 'mkdir testing/output'

                script {
                    def script = "python3 scripts/test_stage.py configurations testing/output " +
		                 "-w ${params.whitelist} -b ${params.blacklist}"
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
                junit testResults: 'testing/reports/*/report.xml' //, allowEmptyResults: true
            }
        }
    }
}
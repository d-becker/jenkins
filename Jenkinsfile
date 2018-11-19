pipeline {
    agent {
        dockerfile {
            args '--mount \'type=volume,src=m2,dst=/root/.m2\''
        }
    }

    parameters {
        string(defaultValue: 'master',
            description: 'Oozie branch, tag or commit. In the Oozie repository, this reference will be checked out ' +
                         'before building and testing.',
            name: 'oozie_branch')
        string(defaultValue: 'configuration',
            description: 'A directory within the test repository (not the Oozie repository) ' +
	                 'that contains dbd BuildConfiguration files. Each BuildConfiguration is built and tested.',
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
                sh 'scripts/build_oozie_and_symlink.sh'
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
                        script_timeout = "-t ${params.timeout}"
                    }

                    def script = script_base + script_build_config_files +
                                 script_whitelist + script_blacklist +
                                 script_validate_only + script_timeout

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
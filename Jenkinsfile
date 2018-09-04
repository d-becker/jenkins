import hudson.plugins.ws_cleanup.Pattern.PatternType

pipeline {
    agent { dockerfile true }
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
        // stage('clone-oozie') {
        //     steps {
        //         sh '/bin/bash -c "cd testing && git clone https://github.com/apache/oozie.git"'
        //     }
        // }
        stage('dbd') {
            steps {
                sh 'mkdir testing/output'

                script {
                    def returnCode = sh (script: 'python3 scripts/test_stage.py configurations testing/output', returnStatus: true)
                    zip (zipFile: 'testing/reports.zip', archive: false, dir: 'testing/reports')
                    archiveArtifacts (artifacts: 'testing/reports.zip')

                    if (returnCode != 0) {
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }
    }
}
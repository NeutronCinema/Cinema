// Jenkinsfile (Declarative Pipeline)
// todo: move to test pipeline
pipeline {
    agent any
    /*
    environment {
        ENV_NAME = 'test-env'
        LOCK_FILE = 'conda-lock.yml'
    }
    */
    stages {
/*
        stage('Check conda installation') {
            steps {
                sh 'conda info'  
            }
        }
*/
        stage('Build linux') {
            parallel {

                stage('Build linux x86') {
                    agent{
                        node{label 'Jenkins_Local'}
                    }
                    steps {
                        echo 'Building Cinema in linux x86'
                        sh 'which conda'
                        sh 'find / -name *conda*'
                        sh 'source ~/.bashrc'
                        sh 'git clone https://code.ihep.ac.cn/cinema-developers/cinema-prompt-feedstock.git ccbuild'
                        sh 'cd ccbuild'
                        sh 'conda build . -c conda-forge'
                    }
                }

                stage('Build linux arm') {
                    agent {
                        node{label 'ncbuilder'}
                    }
                    steps {
                        echo 'Building Cinema in linux arm64'
                        sh 'which conda'
                        sh 'find / -name *conda*'
                        sh 'source ~/.bashrc'
                        sh 'git clone https://code.ihep.ac.cn/cinema-developers/cinema-prompt-feedstock.git ccbuild'
                        sh 'cd ccbuild'
                        sh 'conda build . -c conda-forge'
                    }
                }
            }
        }
    }
    // post {
    //     always {
    //         sh "conda env remove -n ${ENV_NAME}"  // 清理环境
    //         // junit '**/test-results/*.xml'         // 归档测试报告
    //     }
    //     failure {
    //         slackSend channel: '#ci-alerts', message: "构建失败: ${env.JOB_NAME} ${env.BUILD_NUMBER}"
    //     }
    // }
        post {
        success {
            updateGitlabCommitStatus name: 'build', state: 'success'
        }
        failure {
            updateGitlabCommitStatus name: 'build', state: 'failed'
        }
        }
}

// 自定义函数封装测试逻辑
// def runTests(pythonVersion) {
//     withEnv(["PYTHON_VERSION=${pythonVersion}"]) {
//         script {
//             // 动态创建隔离环境
//             def envName = "${ENV_NAME}-py${pythonVersion}"
//             sh """
//                 conda create --clone ${ENV_NAME} --name ${envName}
//                 conda activate ${envName}
//                 conda install -y python=${pythonVersion}
//                 pytest --junitxml=test-results/py${pythonVersion}.xml
//             """
//         }
//     }
// }
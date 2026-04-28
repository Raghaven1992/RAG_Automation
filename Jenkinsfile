pipeline {
    agent any
    parameters {
        string(name: 'PDF_SOURCE_PATH', defaultValue: 'D:/RAG_Automation_V2/RAG_Automation/data', description: 'Local path to PDFs')
    }
    stages {
        stage('Sync Data') {
            steps {
                bat "xcopy /E /I /Y \"${params.PDF_SOURCE_PATH}\" .\\data"
            }
        }
        stage('Docker Deploy') {
            steps {
                // Ensure no fake folders exist from previous mount failures
                bat "if exist prometheus.yml\\ rd /s /q prometheus.yml"
                bat "docker-compose down"
                bat "docker-compose up --build -d"
            }
        }
        stage('Open Dashboards') {
            steps {
                script {
                    echo "Launching Monitoring & Chatbot..."
                    // Start /B runs the command in the background so Jenkins can exit
                    bat 'start "" http://localhost:8501'
                    bat 'start "" http://localhost:9091'
                    bat 'start "" http://localhost:3001'
                }
            }
        }
    }
}

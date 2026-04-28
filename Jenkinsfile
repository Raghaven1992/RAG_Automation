pipeline {
    agent any
    parameters {
        string(name: 'PDF_SOURCE_PATH', defaultValue: 'D:\RAG_Automation_V2\RAG_Automation\data', description: 'Local path to PDFs')
    }
    stages {
        stage('Sync Data') {
            steps {
                bat "xcopy /E /I /Y \"${params.PDF_SOURCE_PATH}\" .\\data"
            }
        }
        stage('Docker Deploy') {
            steps {
                // Clean up accidental folders from typos
                bat "if exist prometheus.yml\\ rd /s /q prometheus.yml"
                bat "docker-compose down"
                bat "docker-compose up --build -d"
            }
        }
        stage('Open Dashboards') {
            steps {
                script {
                    echo "Launching Browser Tabs..."
                    bat "start http://localhost:8501"  // Chatbot
                    bat "start http://localhost:9091"  // Prometheus
                    bat "start http://localhost:3001"  // Grafana
                }
            }
        }
    }
}

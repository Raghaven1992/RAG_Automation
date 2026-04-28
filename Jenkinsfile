pipeline {
    agent any
    parameters {
        string(name: 'PDF_SOURCE_PATH', defaultValue: 'D:/RAG_Automation_V2/RAG_Automation/data', description: 'Source PDF path')
    }
    stages {
        stage('Sync Data') {
            steps {
                bat "xcopy /E /I /Y \"${params.PDF_SOURCE_PATH}\" .\\data"
            }
        }
        stage('Docker Deploy') {
            steps {
                // 1. Clean up mount conflicts
                bat "if exist prometheus.yml\\ rd /s /q prometheus.yml"
                
                // 2. Fix permissions for ChromaDB to prevent "Readonly Database" error
                bat "if exist chroma_db icacls chroma_db /grant Everyone:(OI)(CI)F /T"
                
                // 3. Rebuild and Start
                bat "docker-compose down"
                bat "docker-compose up --build -d"
            }
        }
        stage('Open Dashboards') {
            steps {
                script {
                    echo "Opening Chatbot..."
                    bat 'start "" http://localhost:8501'
                }
            }
        }
    }
}

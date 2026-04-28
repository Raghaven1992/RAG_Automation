pipeline {
    agent any
    parameters {
        string(name: 'PDF_SOURCE_PATH', defaultValue: 'D:/RAG_Automation_V2/RAG_Automation/data', description: 'Local path to PDFs')
    }
    stages {
        stage('Sync Data') {
            steps {
                // Ensure data folder exists in workspace
                bat "if not exist data mkdir data"
                bat "xcopy /E /I /Y \"${params.PDF_SOURCE_PATH}\" .\\data"
            }
        }
        stage('Docker Deploy') {
            steps {
                // Fix permissions for the DB folder to allow the fresh ingestion to write
                bat "if exist chroma_db icacls chroma_db /grant Everyone:(OI)(CI)F /T"
                
                bat "docker-compose down"
                bat "docker-compose up --build -d"
            }
        }
    }
}

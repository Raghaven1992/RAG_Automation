pipeline {
    agent any
    parameters {
        string(name: 'PDF_SOURCE_PATH', defaultValue: 'C:/Users/Raghavendran/Documents/3GPP_Specs', description: 'Local path to PDFs')
    }
    stages {
        stage('Sync Data') {
            steps {
                // Copying PDFs from your Windows path into the project workspace
                bat "xcopy /E /I /Y \"${params.PDF_SOURCE_PATH}\" .\\data"
            }
        }
        stage('Docker Deploy') {
            steps {
                // 1. Let's see EVERY file Jenkins just checked out
                bat "dir /b" 
                
                // 2. Deployment
                bat "docker-compose down"
                bat "docker-compose up --build -d"
            }
        }
    }
}

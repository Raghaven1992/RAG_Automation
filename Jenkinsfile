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
                // 1. Check if prometheus.yml is a directory and delete it if it is
                bat """
                if exist "prometheus.yml\\" (
                echo "Removing fake Prometheus folder..."
                rd /s /q "prometheus.yml"
                )
                """
                // 2. Verify the file exists (for debugging)
                bat "dir prometheus.yml"
                // 3. Deploy
                bat "docker-compose down"
                bat "docker-compose up --build -d"
            }
        }
    }
}

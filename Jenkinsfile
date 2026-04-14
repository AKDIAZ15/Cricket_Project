pipeline {

    agent any

    stages {

        stage('Checkout') {

            steps {

                echo "📥 Checking out code..."

                checkout scm

            }
        }

        stage('Build') {

            steps {

                echo "🔨 Building Docker image..."

                sh 'docker build -t cricket-app .'

            }
        }

        stage('Test') {
    steps {
        echo '🧪 Running tests inside container...'

        sh '''
        docker run --rm cricket-app pytest test_app.py
        '''
    }
}

        stage('Docker Deploy') {

            steps {

                echo "🐳 Starting containers..."

                sh 'docker-compose down || true'
                sh 'docker-compose up -d'

            }
        }

        stage('Cassandra Health Check') {

            steps {

                echo "❤️ Checking Cassandra..."

                sh '''
                sleep 20
                docker exec cassandra-db nodetool status
                '''

            }
        }

    }

    post {

        success {

            echo "✅ Pipeline Completed Successfully"

        }

        failure {

            echo "❌ Pipeline Failed"

        }

    }
}

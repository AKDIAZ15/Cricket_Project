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

                sh '''
                docker build -t cricket-app .
                '''

            }
        }

        stage('Test') {

            steps {

                echo "🧪 Running tests inside container..."

                sh '''
                docker run --rm cricket-app pytest test_app.py
                '''

            }
        }

        stage('Docker Deploy') {

            steps {

                echo '🐳 Cleaning old containers...'

                sh '''
                docker rm -f cassandra-db redis-cache cricket-api || true
                docker-compose down --remove-orphans || true
                '''

                echo '🐳 Starting containers...'

                sh '''
                docker-compose up -d
                '''

            }

        }

        stage('Cassandra Health Check') {

            steps {

                echo "❤️ Checking Cassandra..."

                sh '''
                echo "Waiting for Cassandra to initialize..."

                for i in {1..12}
                do
                    docker exec cassandra-db nodetool status && break
                    echo "Cassandra not ready yet..."
                    sleep 10
                done
                '''

            }

        }

    }

    post {

        success {

            echo "✅ Pipeline Completed Successfully 🎉"

        }

        failure {

            echo "❌ Pipeline Failed"

        }

    }

}
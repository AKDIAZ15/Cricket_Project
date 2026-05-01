pipeline {

    agent any

    environment {
        DOCKER_API_VERSION = '1.43'
        COMPOSE_PROJECT_NAME = 'cricket_project'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Image') {
            steps {
                sh 'docker build -t cricket-app .'
            }
        }

        stage('Test') {
            steps {
                sh 'docker run --rm cricket-app pytest test_app.py'
            }
        }

        stage('Deploy') {
    steps {
        sh '''
        docker compose down --remove-orphans || true
        docker rm -f cassandra-db redis-cache cricket-api dashboard || true
        docker compose up -d --build
        docker compose ps
        '''
    }
}

        stage('Verify App') {

            steps {

                sh '''
                for i in $(seq 1 30)
                do
                    if docker exec cricket-api curl -s http://127.0.0.1:5000/ ; then
                        echo "API Ready"
                        exit 0
                    fi

                    echo "Waiting for cricket-api..."
                    sleep 5
                done

                docker logs cricket-api --tail 100
                exit 1
                '''
            }
        }
    }

    post {

        success {
            echo 'Open: http://127.0.0.1:5000 and http://127.0.0.1:8501'
        }

        failure {
            echo 'Pipeline failed — check logs'
        }
    }
}
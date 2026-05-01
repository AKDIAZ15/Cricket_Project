pipeline {

    agent any

    environment {
        DOCKER_API_VERSION = '1.43'
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                checkout scm
            }
        }

        stage('Build Image') {
            steps {
                echo 'Building Docker image...'

                sh '''
                docker build -t cricket-app .
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests...'

                sh '''
                docker run --rm cricket-app pytest test_app.py
                '''
            }
        }

        stage('Deploy') {

            steps {

                echo 'Stopping old containers...'

                sh '''
                docker rm -f cassandra-db redis-cache cricket-api dashboard 2>$null
                '''

                echo 'Starting Cassandra...'

                sh '''
                docker run -d \
                    --name cassandra-db \
                    -p 9042:9042 \
                    cassandra:4.1
                '''

                echo 'Starting Redis...'

                sh '''
                docker run -d \
                    --name redis-cache \
                    -p 6379:6379 \
                    redis:latest
                '''

                echo 'Waiting for databases...'

                sh '''
                sleep 30
                '''

                echo 'Starting cricket-api...'

                sh '''
                docker run -d \
                    --name cricket-api \
                    -p 5000:5000 \
                    cricket-app
                '''

                echo 'Starting dashboard...'

                sh '''
                docker run -d \
                    --name dashboard \
                    -p 8501:8501 \
                    cricket-app \
                    streamlit run dashboard.py \
                    --server.port=8501 \
                    --server.address=0.0.0.0
                '''

            }
        }

        stage('Verify App') {
    steps {
        sh '''
        echo "Checking API readiness..."

        for i in $(seq 1 30)
        do
            if curl -s http://127.0.0.1:5000/ ; then
                echo "API Ready"
                exit 0
            fi

            echo "Waiting for API..."
            sleep 5
        done

        echo "API failed to start"
        docker logs cricket-api --tail 100

        exit 1
        '''
    }
}

    post {

        success {
            echo 'SUCCESS — Open: http://127.0.0.1:5000 and http://127.0.0.1:8501'
        }

        failure {
            echo 'Pipeline failed — check logs'
        }

    }

}
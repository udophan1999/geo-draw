// Jenkins pipeline for MathMate on the shared mathmate VPS (same shape as Wordime's).
//
// Prerequisites on the Jenkins node (which is the VPS):
//   - Docker with the compose plugin
//   - Traefik in host-network mode, watching the docker socket
//   - The shared Postgres, with a `mathmate` database and role already created (README:
//     "Chạy production bằng Docker", including the Postgres 15 GRANT ON SCHEMA public step)
//   - A managed config file with fileId 'mathmate.mathmate.com' holding the production
//     environment (every variable of .env.example that applies, real values)
//
// The build never touches the production database. The app creates its tables on start.

pipeline {
  agent any

  options {
    timeout(time: 30, unit: 'MINUTES')  // first build compiles pycairo and the web app
    timestamps()
    // Two runs at once would render .env into the same workspace and race each other.
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  triggers {
    githubPush()
  }

  environment {
    COMPOSE_FILE = 'docker-compose.prod.yml'
    IMAGE_NAME   = 'mathmate'
    IMAGE_TAG    = "${env.GIT_COMMIT ? env.GIT_COMMIT.take(7) : env.BUILD_NUMBER}"
    IMAGE        = "${IMAGE_NAME}:${IMAGE_TAG}"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Test') {
      // The whole suite inside the runtime image (Manim, Cairo, FFmpeg): a packaging mistake
      // fails here, not as a broken deploy. Uses its own temp data; no secrets needed.
      steps {
        sh 'docker build --target test -t "$IMAGE_NAME:test" .'
      }
    }

    stage('Build image') {
      // Compose needs .env even to parse the file (${DB_NETWORK}, ${APP_DOMAIN}).
      steps {
        configFileProvider([
          configFile(fileId: 'mathmate.mathmate.com', targetLocation: '.env')
        ]) {
          sh '''
            set -eu
            IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" --env-file .env build
            docker tag "$IMAGE" "$IMAGE_NAME:latest"
          '''
        }
      }
    }

    stage('Deploy') {
      steps {
        configFileProvider([
          configFile(fileId: 'mathmate.mathmate.com', targetLocation: '.env')
        ]) {
          sh '''
            set -eu
            IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" --env-file .env up -d --remove-orphans
            docker compose -f "$COMPOSE_FILE" --env-file .env ps
          '''
        }
      }
    }

    stage('Verify') {
      // "running" is not enough: check the health endpoint, the database, and the public URL.
      steps {
        configFileProvider([
          configFile(fileId: 'mathmate.mathmate.com', targetLocation: '.env')
        ]) {
          sh '''
            set -eu
            # Do NOT source .env: Jenkins runs sh with -x, which would print the secrets.
            # Read only the one non-secret value needed. \\042 = " and \\047 = '.
            APP_DOMAIN="$(sed -n 's/^[[:space:]]*APP_DOMAIN=//p' .env | tr -d '\\042\\047' | head -1)"
            PROBE="import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

            echo "→ Waiting for the health check…"
            ok=""
            for _ in $(seq 1 30); do
              if docker compose -f "$COMPOSE_FILE" --env-file .env exec -T app python -c "$PROBE" 2>/dev/null; then
                ok=1; break
              fi
              sleep 2
            done
            [ -n "$ok" ] || {
              echo "✗ App never became healthy. Probe error:" >&2
              docker compose -f "$COMPOSE_FILE" --env-file .env exec -T app python -c "$PROBE" >&2 || true
              echo "--- last 50 log lines:" >&2
              docker compose -f "$COMPOSE_FILE" --env-file .env logs --tail=50 app >&2
              exit 1
            }

            echo "→ Checking the database (reads the users table)…"
            docker compose -f "$COMPOSE_FILE" --env-file .env exec -T app python -c \
              "from api.state import AppState; from pathlib import Path; s = AppState(Path('/data')); print(len(s.accounts.list_users()), 'accounts'); s.close()"

            if [ -z "$APP_DOMAIN" ]; then
              echo "⚠ APP_DOMAIN not set in the managed config — skipping the public URL check."
            else
              echo "→ Checking https://${APP_DOMAIN} through Traefik…"
              curl -fsS "https://${APP_DOMAIN}/api/health" | grep -q '"ok":true' \
                || echo "⚠ Not reachable at https://${APP_DOMAIN} yet — check DNS and the Traefik labels."
            fi
          '''
        }
      }
    }

    stage('Tag rollback point') {
      steps {
        sh 'docker tag "$IMAGE" "$IMAGE_NAME:previous"'
      }
    }
  }

  post {
    success {
      echo "✓ Deployed MathMate (served by Traefik, no host port published)."
    }
    failure {
      echo "✗ Failed at stage: ${env.STAGE_NAME}"
    }
    always {
      sh 'docker image prune -f --filter "until=168h" || true'
      // Never leave rendered secrets in the workspace between builds.
      sh 'rm -f .env || true'
    }
  }
}

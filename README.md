# Система автоматической диагностики счетчиков газа (ГОСТ)

Прикладной сервис для автоматизации метрологического контроля и оценки технического состояния газовых счетчиков в соответствии со стандартами ГОСТ.

## 🚀 Функционал
- **Расчет перепада давления**: Автоматическая оценка состояния приборов на основе сравнения измеренных и расчетных значений.
- **Верификация данных**: Строгая типизация и валидация физических параметров с использованием **Pydantic**.
- **Высокая доступность**: Развертывание в кластере Kubernetes для обеспечения отказоустойчивости.

## 🛠 Технологический стек
- **Backend**: Python 3.11, FastAPI, Uvicorn.
- **Infrastructure**: Kubernetes (K3s), Traefik Ingress.
- **DevOps**: GitLab CI/CD, Docker, Certbot (SSL/TLS).
- **DNS**: Beget API (для DNS-01 Challenge).

## 🏗 Архитектура и Сеть
Проект реализован по принципу **SSL Termination** на уровне Ingress-контроллера.

1. **Трафик**: Internet (HTTPS) -> Traefik Ingress -> FastAPI Service (HTTP).
2. **SSL/TLS**: Использован метод **DNS-01 Challenge** (Let's Encrypt) через TXT-записи в DNS.
3. **Proxy Headers**: Приложение сконфигурировано для обработки заголовков `X-Forwarded-Proto`, что гарантирует корректную работу HTTPS-редиректов.

## 📦 Развертывание (CI/CD)
Проект полностью автоматизирован через **GitLab CI**:
1. **Build**: Сборка Docker-образа и пуш в Container Registry с тегированием по SHA коммита.
2. **Deploy**: Автоматическое обновление манифестов в кластере K3s через `kubectl`.

## 🔒 Безопасность контейнера (Hardening)
1. **Dockerfile**: Контейнеры в кластере создаются пользователем appuser (UID 1000) с ограниченными правами.
2. **SecurityContext**: В манифесте запрет на root-права и повышение привилегий.

## 💡 Сетевая конфигурация (K3s + Traefik)
1. Real IP Propagation: Настроена передача реального IP-адреса клиента в приложение.
2. Traefik в режиме DaemonSet (для высокой доступности на всех нодах.

### 🗺 Схема прохождения трафика (Traffic Flow)

```mermaid
graph LR
    User([Клиент: 1.2.3.4]) -- "HTTPS (443)" --> VPS["VPS (K3s Node)"]
    
    subgraph Cluster [K3s Cluster]
        Traefik["Traefik (DaemonSet) <br/> externalTrafficPolicy: Local"]
        App["FastAPI Pod <br/> --proxy-headers"]
        Svc["Service <br/> (ClusterIP)"]
    end

    VPS --> Traefik
    Traefik -- "X-Forwarded-For: 1.2.3.4 <br/> X-Forwarded-Proto: https" --> Svc
    Svc --> App
    App -- "Логирование реального IP" --> Log[(Log: 1.2.3.4)]
    
    style User fill:#f9f,stroke:#333,stroke-width:2px
    style Traefik fill:#00adef,stroke:#fff,color:#fff
    style App fill:#05998b,stroke:#fff,color:#fff


### Основные команды управления:
```bash
# Проверка статуса деплоя
kubectl rollout status deployment/fastapi-app

# Просмотр логов приложения
kubectl logs -l app=fastapi —tail=20

Установка (Локально)
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

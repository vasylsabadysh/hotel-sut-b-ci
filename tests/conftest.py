import os
import time
import pytest
import psycopg
import requests
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer


@pytest.fixture(scope="session")
def postgres_container():
    """Запускає PostgreSQL контейнер для тестів"""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def wiremock_container():
    """Запускає WireMock контейнер та чекає його повної готовності"""
    with DockerContainer("wiremock/wiremock:latest").with_exposed_ports(8080) as wiremock:
        host = wiremock.get_container_host_ip()
        port = wiremock.get_exposed_port(8080)
        url = f"http://{host}:{port}"
        
        # Очікуємо готовності WireMock (до 10 секунд), щоб уникнути помилок підключення
        for _ in range(20):
            try:
                res = requests.get(f"{url}/__admin/mappings", timeout=1)
                if res.status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
                
        yield url


@pytest.fixture(autouse=True)
def setup_database(postgres_container):
    connection_url = postgres_container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
    
    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../migrations"))
    if os.path.exists(migrations_dir):
        with psycopg.connect(connection_url) as conn:
            with conn.cursor() as cur:
                for filename in sorted(os.listdir(migrations_dir)):
                    if filename.endswith(".sql"):
                        with open(os.path.join(migrations_dir, filename), "r", encoding="utf-8") as f:
                            try:
                                cur.execute(f.read())
                            except psycopg.errors.DuplicateTable:
                                conn.rollback()
                                cur.execute("TRUNCATE TABLE booking_items, bookings RESTART IDENTITY CASCADE;")
                                cur.execute("INSERT INTO rooms (code, nightly_rate, capacity) VALUES ('ROOM-101', 10000, 4) ON CONFLICT DO NOTHING;")
                                conn.commit()

    yield connection_url

    with psycopg.connect(connection_url) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("TRUNCATE TABLE bookings, rooms CASCADE;")
                conn.commit()
            except Exception:
                conn.rollback()
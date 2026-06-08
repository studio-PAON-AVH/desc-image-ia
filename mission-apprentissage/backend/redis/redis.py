import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

def redis_server_prod():
    """Connexion Redis pour la production"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

def redis_server_dev():
    """Connexion Redis pour le développement"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)

def redis_server_test():
    """Connexion Redis pour les tests"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)
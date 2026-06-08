import redis

def redis_server_prod():
    """Connexion Redis pour la production"""
    return redis.Redis(host='localhost', port=6380, db=0)

def redis_server_test():
    """Connexion Redis pour les tests"""
    return redis.Redis(host='localhost', port=6380, db=1)
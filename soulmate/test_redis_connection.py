import redis

try:
    # Connect to Redis instance (replace with your Redis server details)
    r = redis.StrictRedis(host='redis-18183.c330.asia-south1-1.gce.redns.redis-cloud.com:18183', port=18183, db=0)
    r.ping()  # Send a PING command to Redis to check connectivity
    print("Connected to Redis successfully!")
except redis.ConnectionError as e:
    print(f"Connection failed: {e}")
<<<<<<< HEAD
    
=======
>>>>>>> ed615b208044ad28b7e2a4c3430badadb70be97a

const Redis = require('ioredis');
require('dotenv').config();
const redis = new Redis(process.env.REDIS_URL);
async function clean() {
  await redis.flushall();
  console.log('Redis wiped successfully');
  process.exit(0);
}
clean();

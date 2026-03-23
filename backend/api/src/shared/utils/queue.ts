import { Queue } from 'bullmq';
import { config } from '../config';
import IORedis from 'ioredis';

const connection = {
    url: config.redis.url,
    maxRetriesPerRequest: null,
};

export const processingQueue = new Queue('reconstruction-processing', {
    connection,
});

export const addJobToQueue = async (projectId: string) => {
    await processingQueue.add('reconstruct', { projectId }, {
        attempts: 3,
        backoff: {
            type: 'exponential',
            delay: 1000,
        },
    });
};

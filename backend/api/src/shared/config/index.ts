import dotenv from 'dotenv';
import path from 'path';

// Load environment variables
dotenv.config({ path: path.join(__dirname, '../../../.env') });

const getEnv = (key: string, defaultValue?: string): string => {
    const value = process.env[key] || defaultValue;
    if (!value) {
        throw new Error(`Environment variable ${key} is missing`);
    }
    return value;
};

export const config = {
    port: parseInt(getEnv('PORT', '3000'), 10),
    nodeEnv: getEnv('NODE_ENV', 'development'),
    database: {
        uri: getEnv('MONGODB_URI', 'mongodb://localhost:27017/vokvision'),
    },
    twilio: {
        accountSid: getEnv('TWILIO_ACCOUNT_SID'),
        authToken: getEnv('TWILIO_AUTH_TOKEN'),
        verifyServiceSid: getEnv('TWILIO_VERIFY_SERVICE_SID'),
    },
    jwt: {
        secret: getEnv('JWT_SECRET'),
        expiresIn: getEnv('JWT_EXPIRES_IN', '7d'),
    },
    redis: {
        url: getEnv('REDIS_URL'),
    },
    network: {
        localIp: getEnv('LOCAL_IP'),
    }
};

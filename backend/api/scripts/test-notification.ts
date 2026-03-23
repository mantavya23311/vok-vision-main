import { FcmService } from '../src/shared/services/fcm.service';

/**
 * MANUAL TEST SCRIPT
 * Run this to verify if your FCM configuration is correct.
 * Usage: npx ts-node scripts/test-notification.ts <YOUR_DEVICE_TOKEN>
 */

const testToken = process.argv[2];

if (!testToken) {
    console.error('Please provide a device token: npx ts-node -r tsconfig-paths/register scripts/test-notification.ts YOUR_TOKEN');
    process.exit(1);
}

async function runTest() {
    console.log('Testing FCM notification for token:', testToken);
    try {
        await FcmService.sendNotification(
            testToken,
            'Test Notification',
            'If you see this, FCM is working perfectly! 🚀',
            { type: 'test' }
        );
        console.log('✅ Success! Check your device.');
    } catch (error) {
        console.error('❌ Failed to send notification:', error);
    }
}

runTest();

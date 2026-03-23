import * as admin from 'firebase-admin';
import path from 'path';

// Load service account
const serviceAccountPath = path.join(__dirname, '../../../firebase-service-account.json');

try {
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccountPath),
    });
    console.log('Firebase Admin initialized successfully');
} catch (error) {
    console.error('Firebase Admin initialization error:', error);
}

export class FcmService {
    /**
     * Send a notification to a specific device
     * @param token The FCM registration token of the device
     * @param title Title of the notification
     * @param body Body text of the notification
     * @param data Optional data payload (e.g., download link)
     */
    static async sendNotification(token: string, title: string, body: string, data: any = {}) {
        const message = {
            notification: {
                title,
                body,
            },
            data: {
                ...data,
                click_action: 'FLUTTER_NOTIFICATION_CLICK',
            },
            token,
        };

        try {
            const response = await admin.messaging().send(message);
            console.log('Successfully sent message:', response);
            return response;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }
}

import { Twilio } from 'twilio';
import { config } from '../../shared/config';

class TwilioService {
    private client: Twilio;

    constructor() {
        this.client = new Twilio(config.twilio.accountSid, config.twilio.authToken);
    }

    /**
     * Send an OTP verification code via SMS
     * @param phoneNumber recipient's phone number (with country code)
     */
    async sendVerificationCode(phoneNumber: string) {
        try {
            const verification = await this.client.verify.v2
                .services(config.twilio.verifyServiceSid)
                .verifications.create({ to: phoneNumber, channel: 'sms' });

            return verification;
        } catch (error: any) {
            console.error('Twilio Send Error:', error);
            throw new Error(`Twilio Error: ${error.message || 'Failed to send verification code'}`);
        }
    }

    /**
     * Verify an OTP code provided by the user
     * @param phoneNumber recipient's phone number
     * @param code the code entered by the user
     */
    async checkVerificationCode(phoneNumber: string, code: string) {
        try {
            const verificationCheck = await this.client.verify.v2
                .services(config.twilio.verifyServiceSid)
                .verificationChecks.create({ to: phoneNumber, code });

            return verificationCheck.status === 'approved';
        } catch (error) {
            console.error('Twilio Verify Error:', error);
            throw new Error('Failed to verify code');
        }
    }
}

export const twilioService = new TwilioService();
